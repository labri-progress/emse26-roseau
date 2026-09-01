import csv
import os
import re

from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver


def get_html_content_in_mvn_repository_page(page):
    driver = webdriver.Chrome()
    driver.get('https://mvnrepository.com' + page)
    html = driver.page_source
    driver.quit()
    return html


TOP_LIBS_COUNT = 100
LIBS_BY_PAGE = 10

OUTPUT_PATH = 'output'
LIBS_PAGE_DUMPS_PATH = os.path.join(OUTPUT_PATH, 'mvn_top_repo_dumps')
TOP_LIBS_DUMPED_FILE = os.path.join(OUTPUT_PATH, f'top_{TOP_LIBS_COUNT}_dumped.csv')
TOP_LIBS_PRE_FILTERED_FILE = os.path.join(OUTPUT_PATH, f'top_{TOP_LIBS_COUNT}_pre_filtered.csv')

libs = []

page_dumps_path = os.path.join(os.getcwd(), f'{LIBS_PAGE_DUMPS_PATH}{datetime.now().strftime("%Y%m%d-%H%M%S")}')
os.makedirs(page_dumps_path, exist_ok=True)

for page in range(1, TOP_LIBS_COUNT // LIBS_BY_PAGE + 1):
    page_html = get_html_content_in_mvn_repository_page(f'/popular?p={page}')
    soup = BeautifulSoup(page_html, 'html.parser')

    libs_container = soup.find_all('div', 'im')
    for lib in libs_container:
        if lib.find('div', 'h-ad'): # Skip ads
            continue

        link = lib.find('a').get('href')
        lib_html = get_html_content_in_mvn_repository_page(link)

        file_name = link.removeprefix('/artifact/').replace('/', '_').replace('.', '_') + '.html'
        with open(os.path.join(page_dumps_path, file_name), 'w') as f:
            f.write(lib_html)

for root, dirs, files in os.walk(page_dumps_path):
    for file in files:
        if not file.endswith('.html'):
            continue

        with open(os.path.join(root, file), 'r') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            current_lib = {
                'rank': 0,
                'orga': '',
                'name': '',
                'global_usages': 0,
                'license': '',
                'categories': [],
                'tags': [],
                'last_stable_version': '',
                'repository': '',
                'usages': 0,
                'date': ''
            }

            breadcrumb_container = soup.find('div', 'breadcrumb')
            for idx, child in enumerate(breadcrumb_container.children):
                if idx == 2:
                    current_lib['orga'] = child.text
                elif idx == 3:
                    current_lib['name'] = child.text.removeprefix(' » ').removesuffix('\n')

            metadata_table_container = soup.find('table', 'grid')

            ranks_container = metadata_table_container.find('b', 'rank')
            for rank in ranks_container:
                rank_text = rank.text
                if 'MvnRepository' in rank_text:
                    if res := re.match(r'^#(\d+) in', rank_text):
                        current_lib['rank'] = int(res.group(1))

            if metadata_table_container.find('span', 'b lic') is not None:
                current_lib['license'] = metadata_table_container.find('span', 'b lic').text

            categories_container = metadata_table_container.find_all('a', 'b c')
            for category in categories_container:
                current_lib['categories'].append(category.text)

            tags_container = metadata_table_container.find_all('a', 'b tag')
            for tag in tags_container:
                current_lib['tags'].append(tag.text)

            current_lib['global_usages'] = int(metadata_table_container.find(string='Used By').parent.next_sibling.b.text.removesuffix('\nartifacts').replace(',', ''))

            versions_table_container = soup.find('table', 'grid versions').tbody
            for version_container in versions_table_container:
                version_number_container = version_container.find('a', 'vbtn')
                version_number_classes = version_number_container['class']

                if len(version_number_classes) == 2 and 'release' in version_number_classes:
                    current_lib['last_stable_version'] = version_number_container.text
                    current_lib['repository'] = version_container.find('a', 'b lic').text
                    current_lib['usages'] = int(version_container.find('div', 'pb-usages').text.replace(',', ''))
                    current_lib['date'] = version_container.find('td', 'date').text
                    break

            libs.append(current_lib)

libs = sorted(libs, key=lambda x: int(x['rank']))

fieldnames = ['rank', 'orga', 'name', 'global_usages', 'license', 'categories', 'tags', 'last_stable_version', 'repository', 'usages', 'date']
with open(TOP_LIBS_DUMPED_FILE, 'w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(libs)

CENTRALS_TO_KEEP = ['Central']
TAGS_TO_FILTER = ['android', 'compiler', 'clojure', 'language', 'kotlin', 'scala', 'scalajs']
libs_pre_filtered = []
for lib in libs:
    kept = True
    if lib['repository'] not in CENTRALS_TO_KEEP:
        kept = False
    if any(tag in TAGS_TO_FILTER for tag in lib['tags']):
        kept = False

    libs_pre_filtered.append({**lib, 'kept': kept})

pre_fieldnames = fieldnames + ['kept']
with open(TOP_LIBS_PRE_FILTERED_FILE, 'w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=pre_fieldnames)
    writer.writeheader()
    writer.writerows(libs_pre_filtered)
