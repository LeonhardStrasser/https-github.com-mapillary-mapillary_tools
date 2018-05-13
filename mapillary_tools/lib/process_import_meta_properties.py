import time

import processing
import uploader
from exif_read import ExifRead


def add_meta_tag(mapillary_description,
                 type,
                 key,
                 value):
    if 'MAPMetaTags' in mapillary_description:
        if type in mapillary_description['MAPMetaTags']:
            mapillary_description['MAPMetaTags'][type].append(
                {"key": key,
                 "value": value}
            )
        else:
            mapillary_description['MAPMetaTags'][type] = [
                {"key": key,
                 "value": value}
            ]
    else:
        mapillary_description['MAPMetaTags'] = {
            type: [
                {"key": key,
                 "value": value}
            ]
        }


def finalize_import_properties_process(image,
                                       import_path,
                                       orientation,
                                       device_make,
                                       device_model,
                                       GPS_accuracy,
                                       add_file_name,
                                       add_import_date,
                                       verbose,
                                       mapillary_description={}):
    # always check if there are any command line arguments passed, they will
    if orientation:
        mapillary_description["MAPOrientation"] = orientation
    if device_make:
        mapillary_description['MAPDeviceMake'] = device_make
    if device_model:
        mapillary_description['MAPDeviceModel'] = device_model
    if GPS_accuracy:
        mapillary_description['MAPGPSAccuracyMeters'] = float(GPS_accuracy)

    if add_file_name:
        add_meta_tag(mapillary_description,
                     "strings",
                     "original_file_name",
                     image)

    if add_import_date:
        add_meta_tag(mapillary_description,
                     "dates",
                     "import_date",
                     int(round(time.time() * 1000)))

    add_meta_tag(mapillary_description,
                 "strings",
                 "mapillary_tools_version",
                 "0.0")

    processing.create_and_log_process(image,
                                      import_path,
                                      "import_meta_data_process",
                                      "success",
                                      mapillary_description,
                                      verbose)


def get_import_meta_properties_exif(image, verbose):
    import_meta_data_properties = {}
    try:
        exif = ExifRead(image)
    except:
        if verbose:
            print("Warning, EXIF could not be read for image " +
                  image + ", import properties not read.")
        return None
    try:
        import_meta_data_properties["MAPOrientation"] = exif.extract_orientation(
        )
    except:
        if verbose:
            print("Warning, image orientation tag not in EXIF.")
    try:
        import_meta_data_properties["MAPDeviceMake"] = exif.extract_make(
        )
    except:
        if verbose:
            print("Warning, camera make tag not in EXIF.")
    try:
        import_meta_data_properties["MAPDeviceModel"] = exif.extract_model(
        )
    except:
        if verbose:
            print("Warning, camera model tag not in EXIF.")

    return import_meta_data_properties


def process_import_meta_properties(import_path,
                                   orientation,
                                   device_make,
                                   device_model,
                                   GPS_accuracy,
                                   add_file_name,
                                   add_import_date,
                                   import_meta_source,
                                   import_meta_source_path,
                                   verbose,
                                   rerun):

     # get list of file to process
    process_file_list = processing.get_process_file_list(import_path,
                                                         "import_meta_data_process",
                                                         rerun,
                                                         verbose)
    if not len(process_file_list):
        if verbose:
            print("No images to run import meta data process")
            print("If the images have already been processed and not yet uploaded, they can be processed again, by passing the argument --rerun")
        return

    # sanity checks
    if import_meta_source_path == None and import_meta_source != None and import_meta_source != "exif":
        print("Error, if reading import properties from external file, rather than image EXIF or command line arguments, you need to provide full path to the log file.")
        processing.create_and_log_process_in_list(process_file_list,
                                                  import_path,
                                                  "import_meta_data_process"
                                                  "failed",
                                                  verbose)
        return
    elif import_meta_source != None and import_meta_source != "exif" and not os.path.isfile(import_meta_source_path):
        print("Error, " + import_meta_source_path + " file source of import properties does not exist. If reading import properties from external file, rather than image EXIF or command line arguments, you need to provide full path to the log file.")
        processing.create_and_log_process_in_list(process_file_list,
                                                  import_path,
                                                  "import_meta_data_process"
                                                  "failed",
                                                  verbose)
        return

    # map orientation from degrees to tags
    if orientation:
        orientation = processing.format_orientation(orientation)

    # if not external meta source and not image EXIF meta source, finalize the
    # import properties process
    if not import_meta_source:
        for image in process_file_list:
            finalize_import_properties_process(image,
                                               import_path,
                                               orientation,
                                               device_make,
                                               device_model,
                                               GPS_accuracy,
                                               add_file_name,
                                               add_import_date,
                                               verbose,
                                               {})
    else:
        if import_meta_source == "exif":
            # read import meta from image EXIF and finalize the import
            # properties process
            for image in process_file_list:
                import_meta_data_properties = get_import_meta_properties_exif(
                    image, verbose)
                finalize_import_properties_process(image,
                                                   import_path,
                                                   orientation,
                                                   device_make,
                                                   device_model,
                                                   GPS_accuracy,
                                                   add_file_name,
                                                   add_import_date,
                                                   verbose,
                                                   import_meta_data_properties)
        else:
            # read import meta from json and finalize the import properties
            # process
            pass