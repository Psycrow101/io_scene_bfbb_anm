import bpy
from bpy.props import (
        EnumProperty,
        FloatProperty,
        IntProperty,
        StringProperty,
        )
from bpy_extras.io_utils import (
        ImportHelper,
        ExportHelper,
        )

bl_info = {
    "name": "Battle for Bikini Bottom Animation",
    "author": "Psycrow",
    "version": (0, 0, 1),
    "blender": (2, 81, 0),
    "location": "File > Import-Export",
    "description": "Import / Export BFBB Animation (.anm)",
    "warning": "",
    "wiki_url": "",
    "support": 'COMMUNITY',
    "category": "Import-Export"
}

if "bpy" in locals():
    import importlib
    if "import_bfbb_anm" in locals():
        importlib.reload(import_bfbb_anm)
    if "export_bfbb_anm" in locals():
        importlib.reload(export_bfbb_anm)


class ImportBFBBAnm(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.bfbb_anm"
    bl_label = "Import BFBB Animation"
    bl_options = {'PRESET', 'UNDO'}

    filter_glob: StringProperty(default="*.anm", options={'HIDDEN'})
    filename_ext = ".anm"

    fps: FloatProperty(
        name="FPS",
        description="Value by which the keyframe time is multiplied",
        default=30.0,
    )

    def execute(self, context):
        from . import import_bfbb_anm

        keywords = self.as_keywords(ignore=("filter_glob",
                                            ))

        return import_bfbb_anm.load(context, **keywords)


class ExportBFBBAnm(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.bfbb_anm"
    bl_label = "Export BFBB Animation"
    bl_options = {'PRESET'}

    filter_glob: StringProperty(default="*.anm", options={'HIDDEN'})
    filename_ext = ".anm"

    fps: FloatProperty(
        name="FPS",
        description="Value by which the keyframe time is divided",
        default=30.0,
    )

    endian: EnumProperty(
        name="Endian",
        description="Byte order for the target architecture",
        items={
            ('<', 'Little Endian', 'Little Endian'),
            ('>', 'Big Endian', 'Big Endian')},
        default='<',
    )

    flags: IntProperty(
        name="Flags",
        description="Animation flags",
        default=0,
    )

    def execute(self, context):
        from . import export_bfbb_anm

        return export_bfbb_anm.save(context, self.filepath, self.fps, self.flags, self.endian)


def menu_func_import(self, context):
    self.layout.operator(ImportBFBBAnm.bl_idname,
                         text="BFBB Animation (.anm)")


def menu_func_export(self, context):
    self.layout.operator(ExportBFBBAnm.bl_idname,
                         text="BFBB Animation (.anm)")


classes = (
    ImportBFBBAnm,
    ExportBFBBAnm,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
