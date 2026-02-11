import requests
import json
import re

import config


class UpdateNotFound(Exception):
    pass


def search_for_updates(search_terms: str):
    url = 'https://www.catalog.update.microsoft.com/Search.aspx'
    while True:
        html = requests.get(url, {'q': search_terms}).text
        if 'The website has encountered a problem' not in html:
            break
        # Retry...

    if 'We did not find any results' in html:
        raise UpdateNotFound

    assert '(page 1 of 1)' in html  # we expect only one page of results

    p = r'<a [^>]*?onclick=\'goToDetails\("([a-f0-9\-]+)"\);\'[^>]*?>\s*(.*?)\s*</a>'
    matches = re.findall(p, html)

    p2 = r'<input id="([a-f0-9\-]+)" class="flatBlueButtonDownload\b[^"]*?" type="button" value=\'Download\' />'
    assert [uid for uid, title in matches] == re.findall(p2, html)

    return matches


def get_update_download_urls(update_uid: str):
    input_json = [{
        'uidInfo': update_uid,
        'updateID': update_uid
    }]
    url = 'https://www.catalog.update.microsoft.com/DownloadDialog.aspx'
    html = requests.post(url, {'updateIDs': json.dumps(input_json)}).text

    p = r'\ndownloadInformation\[\d+\]\.files\[\d+\]\.url = \'([^\']+)\';'
    return re.findall(p, html)


def get_update(arch: str, windows_version: str, update_kb: str):
    search_query = update_kb

    if update_kb == 'KB5062663':
        # Normally, identical update packages are available for both 22H2 and
        # 23H2. For this update, however, the 22H2 package is not available.
        assert windows_version == '11-22H2'
        windows_version = '11-23H2'

    if windows_version == '11-21H2':
        package_windows_version = fr'Windows 11'  # first Windows 11 version, no suffix
    elif '-' in windows_version:
        windows_version_split = windows_version.split('-')
        search_query += f' {windows_version_split[1]}'
        package_windows_version = fr'Windows {windows_version_split[0]},? Version {windows_version_split[1]}'
    else:
        search_query += f' {windows_version}'
        package_windows_version = fr'Windows 10 Version {windows_version}'

    search_query += f' {arch}'

    found_updates = search_for_updates(search_query)

    filter_regex = r'\bserver\b|\bDynamic Cumulative Update\b| UUP$'

    found_updates = [update for update in found_updates if not re.search(filter_regex, update[1], re.IGNORECASE)]

    # Replace the pattern, and if after the replacement the item exists, filter it.
    # For example, if there's both Cumulative and Delta, pick Cumulative.
    filter_regex_pairs = [
        [r'^(\d{4}-\d{2} )?Delta ', r'\1Cumulative '],
        [r'\bWindows 10 Version 1909\b', r'Windows 10 Version 1903'],
    ]

    found_update_titles = [update[1] for update in found_updates]
    filtered_updates = []
    for update in found_updates:
        update_title = update[1]
        matched = False
        for search, replace in filter_regex_pairs:
            update_title_sub, num_subs = re.subn(search, replace, update_title)
            if num_subs > 0 and update_title_sub in found_update_titles:
                matched = True
                break

        if not matched:
            filtered_updates.append(update)

    found_updates = filtered_updates

    if len(found_updates) != 1:
        raise Exception(f'Expected one update item, found {len(found_updates)}')

    update_uid, update_title = found_updates[0]
    update_title_pattern = rf'(\d{{4}}-\d{{2}} )?(Cumulative|Delta) Update (Preview )?for {package_windows_version} for (?i:{arch})-based Systems \({update_kb}\)( \(\d+\.\d+\))?'
    assert re.fullmatch(update_title_pattern, update_title), update_title

    return update_uid, update_title


def get_update_from_update_catalog_impl(arch: str, windows_version: str, update_kb: str):
    update_uid, update_title = get_update(arch, windows_version, update_kb)

    download_urls = get_update_download_urls(update_uid)
    if not download_urls:
        raise Exception('Update not found in catalog')

    p = fr'/windows[^-]*-{re.escape(update_kb.lower())}-[^/]*$'
    download_urls = [x for x in download_urls if re.search(p, x)]

    if len(download_urls) != 1:
        raise Exception(f'Expected one update URL, found {len(download_urls)}')

    return download_urls[0]


def get_update_from_update_catalog(arch: str, windows_version: str, update_kb: str):
    if update_kb in config.updates_unsupported:
        return None

    return get_update_from_update_catalog_impl(arch, windows_version, update_kb)
    # try:
    #     return get_update_from_update_catalog_impl(arch, windows_version, update_kb)
    # except UpdateNotFound:
    #     return None
    # except Exception as e:
    #     print(f'Failed to get update: {e}')
    #     return None
