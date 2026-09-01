import git
import os
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile

from distutils.dir_util import copy_tree


JDK_21_LINUX_COMPRESSED_ARCHIVE_URL = 'https://download.java.net/java/GA/jdk21/fd2272bbf8e04c3dbaee13770090416c/35/GPL/openjdk-21_linux-x64_bin.tar.gz'
JDK_21_GITHUB_URL = 'https://github.com/openjdk/jdk21.git'

OUTPUT_PATH = 'output'
JDK_ARCHIVE_PATH = os.path.join(OUTPUT_PATH, 'jdk.tar.gz')
JDK_SOURCES_PATH = os.path.join(OUTPUT_PATH, 'jdk_sources')
OUTPUT_EXTRACT_JMODS_PATH = os.path.join(OUTPUT_PATH, 'jmods')
OUTPUT_JDK_JARS_AND_SRCS_PATH = os.path.join(OUTPUT_PATH, 'jdk')


if os.path.exists(OUTPUT_PATH):
    print('Removing existing output folder...')
    shutil.rmtree(OUTPUT_PATH)
    print('Existing output folder removed!')
os.makedirs(OUTPUT_PATH, exist_ok=True)

print('Downloading JDK 21...')
urllib.request.urlretrieve(JDK_21_LINUX_COMPRESSED_ARCHIVE_URL, JDK_ARCHIVE_PATH)
tar = tarfile.open(JDK_ARCHIVE_PATH, "r:gz")
tar.extractall(OUTPUT_PATH)
tar.close()

os.remove(JDK_ARCHIVE_PATH)
jdk_folder = os.listdir(OUTPUT_PATH)[0]
print(f'JDK 21 extracted to {jdk_folder}')

print('Cloning JDK 21 sources...')
git.Repo.clone_from(JDK_21_GITHUB_URL, JDK_SOURCES_PATH, branch='jdk-21-ga')
print('JDK 21 sources cloned!')

jmods_path = os.path.join(OUTPUT_PATH, jdk_folder, 'jmods')
for jmod in os.listdir(jmods_path):
    if jmod.endswith('.jmod'):
        jmod_name = jmod[:-len('.jmod')]
        jmod_jdk_sources_path = os.path.join(JDK_SOURCES_PATH, 'src', jmod_name, 'share', 'classes')
        if not os.path.exists(jmod_jdk_sources_path):
            print(f'No sources found for {jmod_name}')
            continue

        jmod_output_path = os.path.join(OUTPUT_JDK_JARS_AND_SRCS_PATH, jmod_name)
        jmod_jar_file_path = os.path.join(jmod_output_path, 'lib.jar')
        jmod_src_output_path = os.path.join(jmod_output_path, 'src')
        os.makedirs(jmod_src_output_path, exist_ok=True)

        jmod_path = os.path.join(jmods_path, jmod)
        jmod_extract_path = os.path.join(OUTPUT_EXTRACT_JMODS_PATH, jmod_name)
        with zipfile.ZipFile(jmod_path, 'r') as zip_ref:
            zip_ref.extractall(jmod_extract_path)
        jmod_classes_path = os.path.join(jmod_extract_path, 'classes')

        subprocess.run(['jar', 'cf', jmod_jar_file_path, '-C', jmod_classes_path, '.'])

        copy_tree(jmod_jdk_sources_path, jmod_src_output_path)
