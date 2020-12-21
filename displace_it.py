from typing import Optional
import bpy
import traceback

bl_info = {
    "name": "DisplaceIt",
    "blender": (2, 80, 0),
    "category": "Object",
}

"""
for each selected model
    select the model
    disable all deformation modifiers

    find the shader used by the model
    move the displacement shader slot to the surface



    # perhaps create a new UV in case the origin overlaps


    create a new texture
    create a texture node
    select the texture node

    set renderer to cycles
    set render sample count to 1
    set tiles in performance to the same as the texture resolution

    set bake type to emit
    set bake margin to 0
    run bake

    find the named displacement modifier or create a new one
    set coordiante to UV
    set direction to RGB to XYZ
    space local
    strength = 1
    midlevel = 0
    set connected texture
    selected baked texture
    disable clamp option in colors

    revert all settings
"""


class MaterialManager:
    def __init__(self, material: bpy.types.Material):
        self._material = material
        self._node_tree = material.node_tree
        self._is_valid = False

        self._baked_image_node = None

        self._temp_disp_link = None
        self._surf_node_socket = None
        self._surf_output = None
        self._disp_node_socket = None
        self._disp_output = None

        self._setup()

    def _setup(self):
        # find the output node
        output_node = next((n for n in self._node_tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output),
                           None)
        if output_node is None:
            print(f"Skipping {self._material.name} because there was no output node")
            return

        self._surf_output = output_node.inputs["Surface"]
        self._disp_output = output_node.inputs["Displacement"]

        # find out what displacement was connected to
        disp_links = self._disp_output.links
        if not disp_links:
            print(f"Skipping {self._material.name} because there was no displacement specified")
            # no node connected to displacement
            return

        self._is_valid = True
        self._disp_node_socket = disp_links[0].from_socket

        # disconnect the displacement node
        self._node_tree.links.remove(disp_links[0])

        # find out what Surface was connected to
        surf_links = self._surf_output.links
        if surf_links:
            self._surf_node_socket = surf_links[0].from_socket
            # disconnect the surface link
            self._node_tree.links.remove(surf_links[0])
        else:
            self._surf_node_socket = None

        # connect the old displacement output to the surface input
        self._temp_disp_link = self._node_tree.links.new(self._disp_node_socket, self._surf_output)

    @property
    def is_valid(self):
        """Does the material have a displacement output."""
        return self._is_valid

    def setup_baked_texture(self, disp_image: bpy.types.Image):
        """Set up an image texture node and make it active."""
        # create a new image texture node
        self._baked_image_node = self._node_tree.nodes.new('ShaderNodeTexImage')

        # attach the image to the texture node
        self._baked_image_node.image = disp_image

        # select the node
        self._node_tree.nodes.active = self._baked_image_node

    def reset(self):
        """Reset the material."""
        print(f"resetting material settings for {self._material.name}")
        if self._baked_image_node is not None:
            self._node_tree.nodes.remove(self._baked_image_node)

        if self.is_valid:
            # reset to the original state
            self._node_tree.links.remove(self._temp_disp_link)
            if self._surf_node_socket is not None:
                self._node_tree.links.new(self._surf_node_socket, self._surf_output)
            self._node_tree.links.new(self._disp_node_socket, self._disp_output)
        print(f"finished resetting material settings for {self._material.name}")


def displace_obj(context: bpy.types.Context, obj: bpy.types.Object, res: int, inplace=False) -> Optional[str]:
    """Given an object will bake a height texture and create a displacement modifier."""
    if obj.type != "MESH":
        # object is not a mesh
        return
    # select the model
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    context.view_layer.objects.active = obj

    if not inplace:
        # duplicate the object
        new_obj = obj.copy()
        new_obj.data = obj.data.copy()
        context.collection.objects.link(new_obj)
        obj.hide_set(True)
        obj = new_obj

    # disable all deformation modifiers
    for mod in obj.modifiers.values():
        if mod.type == "DISPLACE":
            mod.show_viewport = False
            mod.show_render = False

    materials = [MaterialManager(mat) for mat in obj.data.materials.values()]
    if any(mat.is_valid for mat in materials):
        try:
            img_name = f"__{obj.name}_disp__"
            if img_name in bpy.data.images and bpy.data.images[img_name].is_float and all(
                    r == res for r in bpy.data.images[img_name].size):
                """Check the image more"""
                disp_image = bpy.data.images[img_name]
            else:
                if img_name in bpy.data.images:
                    # remove the image so it can be recreated
                    bpy.data.images.remove(bpy.data.images[img_name])
                # create the image
                bpy.ops.image.new(
                    name=img_name,
                    width=res,
                    height=res,
                    color=(0.0, 0.0, 0.0, 1.0),
                    alpha=False,
                    generated_type="BLANK",
                    float=True,
                    use_stereo_3d=False
                )
                # get the image
                # there is an issue with Blender here where if you create a new texture with the
                # same name it will be given an extension but there is no way to know what that is.
                disp_image = bpy.data.images[img_name]

            # set up an image output for each material the object uses
            for mat in materials:
                if mat.is_valid:
                    mat.setup_baked_texture(disp_image)

            # save the original settings (render)
            sample_count = context.scene.cycles.samples

            # performance
            tiles_x = context.scene.render.tile_x
            tiles_y = context.scene.render.tile_y

            try:
                # set the required settings
                print("Setting render settings")
                context.scene.cycles.samples = 1
                context.scene.render.tile_x = res
                context.scene.render.tile_y = res

                print("baking image")
                bpy.ops.object.bake(
                    type='EMIT',
                    margin=0,
                    use_clear=True,
                )
                print("finished baking image")
            except Exception as e:
                raise e
            finally:
                # reset to original state
                print("resetting render settings")
                context.scene.cycles.samples = sample_count
                context.scene.render.tile_x = tiles_x
                context.scene.render.tile_y = tiles_y

            # set up the texture
            if img_name in bpy.data.textures:
                disp_texture = bpy.data.textures[img_name]
            else:
                disp_texture = bpy.data.textures.new(img_name, type='IMAGE')
            disp_texture.image = disp_image
            disp_texture.use_alpha = False
            disp_texture.use_clamp = False

            # create the displace modifier if it does not exist
            if obj.modifiers[-1].type != "DISPLACE":
                bpy.ops.object.modifier_add("Displace", type='DISPLACE')
            disp_mod = obj.modifiers[-1]

            # enable the displace modifier
            disp_mod.show_viewport = True
            disp_mod.show_render = True
            disp_mod.direction = "RGB_TO_XYZ"
            disp_mod.mid_level = 0.0
            disp_mod.space = "LOCAL"
            disp_mod.strength = 1.0
            disp_mod.texture = disp_texture
            disp_mod.texture_coords = "UV"

        except Exception as e:
            raise e
        finally:
            # reset to the original state
            for mat in materials:
                mat.reset()

    return obj.name


def displace_selected(context: bpy.types.Context, resolution: int, inplace=False):
    if context.scene.render.engine != "CYCLES":
        raise Exception("Cycles must be enabled")

    selected = [obj.name for obj in context.selected_objects]
    final_selected = []
    active_name = context.view_layer.objects.active.name

    # for each selected model
    for obj in context.selected_objects:
        try:
            obj_name = displace_obj(context, obj, resolution, inplace)
            if obj_name is not None:
                final_selected.append(obj_name)
            if obj.name == active_name:
                active_name = obj_name
        except:
            traceback.print_exc()

    # select the originally selected model
    context.view_layer.objects.active = bpy.data.objects[active_name]
    for obj_name in final_selected:
        obj = bpy.data.objects[obj_name]
        obj.select_set(True)


class DisplaceIt(bpy.types.Operator):
    """Convert Shader Displacement to Mesh Displacement."""
    bl_idname = "object.displace_it"
    bl_label = "DisplaceIt"
    bl_options = {'REGISTER', 'UNDO'}

    inplace: bpy.props.BoolProperty(name="Inplace", default=True)
    res: bpy.props.IntProperty(name="Resolution", default=512, min=128, max=65536)

    def execute(self, context: bpy.types.Context):
        displace_selected(context, self.res, self.inplace)
        return {'FINISHED'}


def menu_func(self, context: bpy.types.Context):
    self.layout.operator(DisplaceIt.bl_idname)


def register():
    bpy.utils.register_class(DisplaceIt)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.utils.unregister_class(DisplaceIt)
    bpy.types.VIEW3D_MT_object.remove(menu_func)


if __name__ == "__main__":
    register()
