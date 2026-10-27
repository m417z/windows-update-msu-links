from pathlib import Path


out_path = Path('.')

windows_versions_unsupported = {}

updates_unsupported = {
    # Windows Server only.
    'KB5070881',
    'KB5070882',
    'KB5070883',
    'KB5072359',

    # Missing on the Update Catalog.
    'KB5071959',
}

update_archs_unsupported = {
    # ARM64 only.
    ('KB5134134', 'x64'),
}
