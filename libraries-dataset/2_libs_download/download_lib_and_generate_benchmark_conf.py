import csv
import os
import urllib.request
import zipfile


LIBS_TO_DOWNLOAD_CSV_FILE = 'libs_to_download.csv'
LIBRARIES_STATE_TEMPLATE_FILE = 'LibrariesState.template'

OUTPUT_PATH = 'output'
LIBS_DOWNLOADED_PATH = os.path.join(OUTPUT_PATH, 'libs')
LIBRARIES_STATE_JAVA_FILE = os.path.join(OUTPUT_PATH, 'LibrariesState.java')

MAVEN_CENTRAL_REPO_URL = 'https://repo1.maven.org/maven2'


def item_line_count(path):
    if os.path.isdir(path):
        return dir_line_count(path)
    elif os.path.isfile(path) and path.endswith('.java'):
        return len(open(path, 'rb').readlines())
    else:
        return 0


def dir_line_count(dir):
    return sum(map(lambda item: item_line_count(os.path.join(dir, item)), os.listdir(dir)))


os.makedirs(LIBS_DOWNLOADED_PATH, exist_ok=True)

libs_to_download = []
with open(LIBS_TO_DOWNLOAD_CSV_FILE, 'r') as file:
    csvFile = csv.DictReader(file)
    for row in csvFile:
        if row['kept'] == 'True':
            libs_to_download.append(row)

lib_names = []
for lib in libs_to_download:
    orga = lib['orga']
    name = lib['name']
    version = lib['last_stable_version']

    root_url = f"{MAVEN_CENTRAL_REPO_URL}/{orga.replace('.', '/')}/{name}/{version}"
    root_package_name = f'{name}-{version}'
    jar_url = f"{root_url}/{root_package_name}.jar"
    sources_url = f"{root_url}/{root_package_name}-sources.jar"

    root_lib_download_path = os.path.join(LIBS_DOWNLOADED_PATH, root_package_name)
    jar_download_path = os.path.join(root_lib_download_path, 'lib.jar')
    sources_download_path = os.path.join(root_lib_download_path, 'src.jar')
    sources_extract_path = os.path.join(root_lib_download_path, 'src')

    os.makedirs(root_lib_download_path, exist_ok=True)

    try:
        urllib.request.urlretrieve(jar_url, jar_download_path)
        urllib.request.urlretrieve(sources_url, sources_download_path)

        with zipfile.ZipFile(sources_download_path, 'r') as zip_ref:
            zip_ref.extractall(sources_extract_path)
        os.remove(sources_download_path)

        line_count = dir_line_count(sources_extract_path)

        if line_count > 0:
            lib_names.append(root_package_name)
        else:
            print(f'No Java sources for {root_package_name}, skipping')
    except Exception as e:
        print(f'Error downloading in {root_url}: {e}')
        os.rmdir(root_lib_download_path)
        continue


with open(LIBRARIES_STATE_TEMPLATE_FILE, 'r') as template_file:
    content = template_file.read().replace('<LIBS_TO_ANALYZE>', '", "'.join(lib_names))

    with open(LIBRARIES_STATE_JAVA_FILE, 'w') as file:
        file.write(content)
