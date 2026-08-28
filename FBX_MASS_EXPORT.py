bl_info = {
    "name": "FBX Mass Export mesh",
    "author": "L1ra",
    "version": (0, 3, 0),
    "blender": (4, 3, 2),
    "location": "File > Export > FBX > Batch Export",
    "description": "Adds batch export to the native FBX export dialog",
    "category": "Import-Export",
}



import bpy
import os
import sys
import subprocess
from bpy.props import BoolProperty
from bpy.types import Operator, Panel, PropertyGroup



def GetMeshCollectionName(obj):
    for col in obj.users_collection:
        if col.name != "Scene Collection":
            return col.name
    return None



def CollectExportGroups(context, props, useSelection=False):
    if useSelection:
        pool = [o for o in context.selected_objects if o.type == "MESH"]
    else:
        pool = [o for o in context.scene.objects if o.type == "MESH"]

    groups = []

    if props.groupByParent:
        parent_map = {}
        standalone = []
        for obj in pool:
            if obj.parent and obj.parent.type == "MESH":
                if obj.parent not in parent_map:
                    parent_map[obj.parent] = []
                parent_map[obj.parent].append(obj)
            else:
                standalone.append(obj)

        for parent, children in parent_map.items():
            if parent.fbxBatchExclude:
                continue
            col_name = GetMeshCollectionName(parent) if props.useCollectionFolders else None
            groups.append((parent.name, col_name, children, parent))

        for obj in standalone:
            if obj.fbxBatchExclude:
                continue
            col_name = GetMeshCollectionName(obj) if props.useCollectionFolders else None
            groups.append((obj.name, col_name, [obj], obj))
    else:
        for obj in pool:
            if obj.fbxBatchExclude:
                continue
            col_name = GetMeshCollectionName(obj) if props.useCollectionFolders else None
            groups.append((obj.name, col_name, [obj], obj))

    return groups



class FbxBatchProps(PropertyGroup):
    useCollectionFolders: BoolProperty(
        name="By Collection",
        description="Export each mesh into a subfolder named after its collection",
        default=False,
    )
    groupByParent: BoolProperty(
        name="Group by Parent",
        description="Meshes that share a mesh parent are combined into one FBX named after the parent",
        default=False,
    )
    openAfterExport: BoolProperty(
        name="Open Folder",
        description="Open the output folder after export finishes",
        default=True,
    )
    showPreview: BoolProperty(
        name="Preview",
        description="Show list of objects that will be exported",
        default=True,
    )



class MeshFbxBatchExporter:
    def __init__(self, context, fbxOp, props):
        self.context = context
        self.fbxOp = fbxOp
        self.props = props
        self.outputDir = os.path.dirname(bpy.path.abspath(fbxOp.filepath))
        self.exportedCount = 0
        self.failedNames = []


    def StashSelection(self):
        selected = {o for o in self.context.view_layer.objects if o.select_get()}
        active = self.context.view_layer.objects.active
        for obj in self.context.view_layer.objects:
            obj.select_set(False)
        return selected, active


    def RestoreSelection(self, state):
        selected, active = state
        for obj in self.context.view_layer.objects:
            obj.select_set(obj in selected)
        self.context.view_layer.objects.active = active


    def BuildSettings(self, filepath):
        op = self.fbxOp
        return {
            "filepath":                         filepath,
            "use_selection":                    True,
            "use_visible":                      op.use_visible,
            "use_active_collection":            op.use_active_collection,
            "global_scale":                     op.global_scale,
            "apply_unit_scale":                 op.apply_unit_scale,
            "apply_scale_options":              op.apply_scale_options,
            "use_space_transform":              op.use_space_transform,
            "bake_space_transform":             op.bake_space_transform,
            "object_types":                     {"MESH"},
            "use_mesh_modifiers":               op.use_mesh_modifiers,
            "use_mesh_modifiers_render":        op.use_mesh_modifiers_render,
            "mesh_smooth_type":                 op.mesh_smooth_type,
            "colors_type":                      op.colors_type,
            "prioritize_active_color":          op.prioritize_active_color,
            "use_subsurf":                      op.use_subsurf,
            "use_mesh_edges":                   op.use_mesh_edges,
            "use_tspace":                       op.use_tspace,
            "use_triangles":                    op.use_triangles,
            "use_custom_props":                 op.use_custom_props,
            "add_leaf_bones":                   op.add_leaf_bones,
            "primary_bone_axis":                op.primary_bone_axis,
            "secondary_bone_axis":              op.secondary_bone_axis,
            "use_armature_deform_only":         op.use_armature_deform_only,
            "armature_nodetype":                op.armature_nodetype,
            "bake_anim":                        op.bake_anim,
            "bake_anim_use_all_bones":          op.bake_anim_use_all_bones,
            "bake_anim_use_nla_strips":         op.bake_anim_use_nla_strips,
            "bake_anim_use_all_actions":        op.bake_anim_use_all_actions,
            "bake_anim_force_startend_keying":  op.bake_anim_force_startend_keying,
            "bake_anim_step":                   op.bake_anim_step,
            "bake_anim_simplify_factor":        op.bake_anim_simplify_factor,
            "path_mode":                        op.path_mode,
            "embed_textures":                   op.embed_textures,
            "batch_mode":                       "OFF",
            "use_batch_own_dir":                op.use_batch_own_dir,
            "axis_forward":                     op.axis_forward,
            "axis_up":                          op.axis_up,
        }


    def ExportGroup(self, name, col_name, objects):
        for obj in objects:
            obj.select_set(True)
        if objects:
            self.context.view_layer.objects.active = objects[0]

        folder = os.path.join(self.outputDir, col_name) if col_name else self.outputDir
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, name + ".fbx")

        try:
            bpy.ops.export_scene.fbx(**self.BuildSettings(filepath))
            self.exportedCount += 1
            print(f"  ✓  {name}  →  {filepath}")
        except Exception as error:
            self.failedNames.append(name)
            print(f"  ✗  {name}  ERROR: {error}")
        finally:
            for obj in objects:
                obj.select_set(False)


    def OpenFolder(self):
        if sys.platform == "win32":
            subprocess.Popen(["explorer", self.outputDir])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", self.outputDir])
        else:
            subprocess.Popen(["xdg-open", self.outputDir])


    def Run(self):
        groups = CollectExportGroups(self.context, self.props, self.fbxOp.use_selection)
        if not groups:
            return groups, False

        os.makedirs(self.outputDir, exist_ok=True)
        state = self.StashSelection()

        wm = self.context.window_manager
        wm.progress_begin(0, len(groups))
        for i, (name, col_name, objects, _key) in enumerate(groups):
            wm.progress_update(i)
            self.ExportGroup(name, col_name, objects)
        wm.progress_end()

        self.RestoreSelection(state)

        if self.props.openAfterExport:
            self.OpenFolder()

        return groups, True



class FBXBATCH_OT_export(Operator):
    bl_idname = "fbxbatch.export"
    bl_label = "Export All Meshes"
    bl_description = "Export every mesh in the scene as a separate .fbx using current dialog settings"

    def execute(self, context):
        fbxOp = context.space_data.active_operator
        props = context.scene.fbxBatchProps
        exporter = MeshFbxBatchExporter(context, fbxOp, props)
        groups, hasTargets = exporter.Run()

        if not hasTargets:
            self.report({"WARNING"}, "No mesh objects found")
            return {"CANCELLED"}

        if exporter.failedNames:
            failed = ", ".join(exporter.failedNames)
            self.report({"WARNING"}, f"Exported {exporter.exportedCount}/{len(groups)}. Failed: {failed}")
        else:
            self.report({"INFO"}, f"Done — {exporter.exportedCount} file(s) saved to {exporter.outputDir}")

        return {"FINISHED"}



class FILE_PT_fbxBatch(Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_label = "Batch Export"
    bl_parent_id = "FILE_PT_operator"
    bl_options = {"DEFAULT_CLOSED"}
    bl_order = 100

    @classmethod
    def poll(cls, context):
        return (
            hasattr(context.space_data, "active_operator")
            and context.space_data.active_operator.bl_idname == "EXPORT_SCENE_OT_fbx"
        )


    def draw(self, context):
        layout = self.layout
        props = context.scene.fbxBatchProps
        fbxOp = context.space_data.active_operator
        groups = CollectExportGroups(context, props, fbxOp.use_selection)
        count = len(groups)

        box = layout.box()
        col = box.column(align=True)

        row = col.row(align=True)
        row.prop(props, "useCollectionFolders", icon="OUTLINER_COLLECTION")
        row.prop(props, "groupByParent", icon="OUTLINER_OB_EMPTY")

        row = col.row(align=True)
        row.prop(props, "openAfterExport", icon="FILE_FOLDER")
        row.prop(props, "showPreview", icon="HIDE_OFF" if props.showPreview else "HIDE_ON")

        if props.showPreview:
            layout.separator(factor=0.3)
            box = layout.box()

            header = box.row()
            scope = "selected" if fbxOp.use_selection else "scene"
            header.label(
                text=f"{count} {'file' if count == 1 else 'files'}  ·  {scope}",
                icon="MESH_DATA",
            )

            pool = (
                [o for o in context.selected_objects if o.type == "MESH"]
                if fbxOp.use_selection
                else [o for o in context.scene.objects if o.type == "MESH"]
            )

            if pool:
                col = box.column(align=True)

                if props.groupByParent:
                    drawn_parents = set()
                    standalone = []
                    for obj in pool:
                        if obj.parent and obj.parent.type == "MESH":
                            if obj.parent not in drawn_parents:
                                drawn_parents.add(obj.parent)
                                children = [o for o in pool if o.parent == obj.parent]
                                self.DrawGroupRow(col, obj.parent.name, children, obj.parent, props)
                        else:
                            standalone.append(obj)
                    for obj in standalone:
                        self.DrawObjectRow(col, obj, props)
                else:
                    for obj in pool:
                        self.DrawObjectRow(col, obj, props)
            else:
                row = box.row()
                row.alert = True
                label = "Nothing selected" if fbxOp.use_selection else "No mesh objects in scene"
                row.label(text=label, icon="ERROR")

        layout.separator(factor=0.5)

        row = layout.row()
        row.scale_y = 1.4
        row.enabled = count > 0
        row.operator(
            "fbxbatch.export",
            text=f"Export All Meshes  ({count})" if count else "No Meshes Found",
            icon="EXPORT",
        )


    def DrawObjectRow(self, col, obj, props):
        row = col.row(align=True)
        excluded = obj.fbxBatchExclude
        icon = "CHECKBOX_DEHLT" if excluded else "CHECKBOX_HLT"
        row.prop(obj, "fbxBatchExclude", text="", icon=icon, emboss=False, invert_checkbox=True)
        sub = row.row()
        sub.active = not excluded
        label = obj.name if len(obj.name) <= 26 else obj.name[:24] + "…"
        sub.label(text=label, icon="MESH_DATA")
        col_name = GetMeshCollectionName(obj) if props.useCollectionFolders else None
        if col_name:
            right = sub.row()
            right.alignment = "RIGHT"
            right.label(text=col_name, icon="OUTLINER_COLLECTION")


    def DrawGroupRow(self, col, name, children, key_obj, props):
        row = col.row(align=True)
        excluded = key_obj.fbxBatchExclude
        icon = "CHECKBOX_DEHLT" if excluded else "CHECKBOX_HLT"
        row.prop(key_obj, "fbxBatchExclude", text="", icon=icon, emboss=False, invert_checkbox=True)
        sub = row.row()
        sub.active = not excluded
        label = name if len(name) <= 22 else name[:20] + "…"
        sub.label(text=label, icon="OUTLINER_OB_EMPTY")
        right = sub.row()
        right.alignment = "RIGHT"
        col_name = GetMeshCollectionName(key_obj) if props.useCollectionFolders else None
        if col_name:
            right.label(text=col_name, icon="OUTLINER_COLLECTION")
        right.label(text=f"{len(children)} meshes")


registeredClasses = (
    FbxBatchProps,
    FBXBATCH_OT_export,
    FILE_PT_fbxBatch,
)



def register():
    for cls in registeredClasses:
        bpy.utils.register_class(cls)
    bpy.types.Scene.fbxBatchProps = bpy.props.PointerProperty(type=FbxBatchProps)
    bpy.types.Object.fbxBatchExclude = BoolProperty(
        name="Exclude from Batch",
        description="Skip this object during batch FBX export",
        default=False,
    )



def unregister():
    del bpy.types.Scene.fbxBatchProps
    del bpy.types.Object.fbxBatchExclude
    for cls in reversed(registeredClasses):
        bpy.utils.unregister_class(cls)



if __name__ == "__main__":
    register()