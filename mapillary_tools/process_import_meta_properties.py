import os
import sys
import time
import typing as T

from tqdm import tqdm

from . import processing, VERSION
from .error import print_error
from .exif_read import ExifRead
from .types import MetaProperties


META_DATA_TYPES = {
    "strings": str,
    "doubles": float,
    "longs": int,
    "dates": int,
    "booleans": bool,
}


def add_meta_tag(desc: MetaProperties, tag_type: str, key: str, value_before) -> None:
    type_ = META_DATA_TYPES.get(tag_type)

    if type_ is None:
        raise RuntimeError(f"Invalid tag type: {tag_type}")

    try:
        value = type_(value_before)
    except (ValueError, TypeError) as ex:
        raise RuntimeError(
            f'Unable to parse "{key}" in the custom metatags as {tag_type}'
        ) from ex

    meta_tag = {"key": key, "value": value}
    tags = desc.setdefault("MAPMetaTags", {})
    tags.setdefault(tag_type, []).append(meta_tag)


def parse_and_add_custom_meta_tags(desc: MetaProperties, custom_meta_data: str) -> None:
    # parse entry
    meta_data_entries = custom_meta_data.split(";")
    print(meta_data_entries)
    for entry in meta_data_entries:
        # parse name, type and value
        entry_fields = entry.split(",")
        if len(entry_fields) != 3:
            raise RuntimeError(
                f'Unable to parse tag "{entry}" -- it must be "name,type,value"'
            )
        # set name, type and value
        tag_name = entry_fields[0]
        tag_type = entry_fields[1] + "s"
        tag_value = entry_fields[2]

        add_meta_tag(desc, tag_type, tag_name, tag_value)


def finalize_import_properties_process(
    image: str,
    desc: MetaProperties,
    import_path: str,
    orientation=None,
    device_make=None,
    device_model=None,
    GPS_accuracy=None,
    add_file_name=False,
    add_import_date=False,
    verbose=False,
    custom_meta_data=None,
    camera_uuid=None,
    windows_path=False,
    exclude_import_path=False,
    exclude_path=None,
):
    # always check if there are any command line arguments passed, they will
    if orientation is not None:
        desc["MAPOrientation"] = orientation
    if device_make is not None:
        desc["MAPDeviceMake"] = device_make
    if device_model is not None:
        desc["MAPDeviceModel"] = device_model
    if GPS_accuracy is not None:
        desc["MAPGPSAccuracyMeters"] = float(GPS_accuracy)
    if camera_uuid is not None:
        desc["MAPCameraUUID"] = camera_uuid
    if add_file_name:
        image_path = image
        if exclude_import_path:
            image_path = image_path.replace(import_path, "").lstrip("\\").lstrip("/")
        elif exclude_path:
            image_path = image_path.replace(exclude_path, "").lstrip("\\").lstrip("/")
        if windows_path:
            image_path = image_path.replace("/", "\\")

        desc["MAPFilename"] = image_path

    if add_import_date:
        add_meta_tag(
            desc,
            "dates",
            "import_date",
            int(round(time.time() * 1000)),
        )

    add_meta_tag(desc, "strings", "mapillary_tools_version", VERSION)

    if custom_meta_data:
        parse_and_add_custom_meta_tags(desc, custom_meta_data)

    processing.create_and_log_process(
        image, "import_meta_data_process", "success", desc, verbose
    )


def get_import_meta_properties_exif(image: str) -> T.Optional[MetaProperties]:
    import_meta_data_properties: MetaProperties = {}
    try:
        exif = ExifRead(image)
    except:
        print(
            "Warning, EXIF could not be read for image "
            + image
            + ", import properties not read."
        )
        return None
    import_meta_data_properties["MAPOrientation"] = exif.extract_orientation()
    import_meta_data_properties["MAPDeviceMake"] = exif.extract_make()
    import_meta_data_properties["MAPDeviceModel"] = exif.extract_model()
    import_meta_data_properties["MAPMetaTags"] = eval(exif.extract_image_history())

    return import_meta_data_properties


def process_import_meta_properties(
    import_path,
    orientation=None,
    device_make=None,
    device_model=None,
    GPS_accuracy=None,
    add_file_name=False,
    add_import_date=False,
    verbose=False,
    rerun=False,
    skip_subfolders=False,
    video_import_path=None,
    custom_meta_data=None,
    camera_uuid=None,
    windows_path=False,
    exclude_import_path=False,
    exclude_path=None,
) -> None:
    # sanity check if video file is passed
    if (
        video_import_path
        and not os.path.isdir(video_import_path)
        and not os.path.isfile(video_import_path)
    ):
        print("Error, video path " + video_import_path + " does not exist, exiting...")
        sys.exit(1)

    # in case of video processing, adjust the import path
    if video_import_path:
        # set sampling path
        video_sampling_path = "mapillary_sampled_video_frames"
        video_dirname = (
            video_import_path
            if os.path.isdir(video_import_path)
            else os.path.dirname(video_import_path)
        )
        import_path = (
            os.path.join(os.path.abspath(import_path), video_sampling_path)
            if import_path
            else os.path.join(os.path.abspath(video_dirname), video_sampling_path)
        )

    if not import_path or not os.path.isdir(import_path):
        print_error(
            "Error, import directory " + import_path + " does not exist, exiting..."
        )
        sys.exit(1)

    process_file_list = processing.get_process_file_list(
        import_path, "import_meta_data_process", rerun, skip_subfolders=skip_subfolders
    )
    if not process_file_list:
        print("No images to run import meta data process")
        return

    if orientation is not None:
        orientation = processing.format_orientation(orientation)

    for image in tqdm(
        process_file_list, unit="files", desc="Processing import meta properties"
    ):
        import_meta_data_properties = get_import_meta_properties_exif(image)
        if import_meta_data_properties is None:
            processing.create_and_log_process(
                image, "import_meta_data_process", "failed", {}, verbose
            )
        else:
            finalize_import_properties_process(
                image,
                import_meta_data_properties,
                import_path,
                orientation,
                device_make,
                device_model,
                GPS_accuracy,
                add_file_name,
                add_import_date,
                verbose,
                custom_meta_data,
                camera_uuid,
                windows_path,
                exclude_import_path,
                exclude_path,
            )
