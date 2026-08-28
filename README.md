# FBX Mass Export for Blender

A lightweight Blender addon for batch exporting meshes as individual FBX files with customizable settings.

## Features

- **Per-mesh export**: Each mesh exports as a separate `.fbx` file with its Blender name
- **Native UI integration**: Works within Blender's standard FBX export dialog
- **Flexible grouping**:
  - Export by collection (creates subfolders)
  - Group child meshes under parent object
- **Live preview**: See exactly which objects will be exported
- **Exclusion system**: Toggle individual objects/groups in the preview panel
- **Post-export actions**: Automatically open output folder when done

## Installation
1. Download `FBX_MASS_EXPORT.py`
2. In Blender: `Edit > Preferences > Add-ons > Install from disk > Select the downloaded file`
3. Enable "FBX Mass Export"

## Usage
1. Open standard FBX export (`File > Export > FBX`)
2. Configure your export settings as usual
3. Use the **Batch Export** panel to:
   - Toggle grouping options
   - Preview/exclude objects
   - Execute batch export

## Requirements
- Blender 4.3+
- No external dependencies
