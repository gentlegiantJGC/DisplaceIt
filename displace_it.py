import bpy
import traceback


def displace(context, obj, res: int, inplace=False):
    """Given an object will bake a height texture and create a displacement modifier."""
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
    
    # find the materia used by the model
    if obj.vertex_groups:
        return
        # need to work this part out
        
    else:
        if len(obj.data.materials) > 1:
            return
            # need to work this part out
        else:
            material = obj.data.materials[0]
            node_tree = material.node_tree
            vert_group = 0

            # find the output node
            output_node = next((n for n in node_tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None)
            if output_node is None:
                print(f"Skipping {obj.name} because there was no output node")
                # no output node
                return
            
            surf_output = output_node.inputs["Surface"]
            disp_output = output_node.inputs["Displacement"]

            
            # find out what displacement was connected to
            disp_links = disp_output.links
            if not disp_links:
                print(f"Skipping {obj.name} because there was no displacement specified")
                # no node connected to displacement
                return
            disp_node_socket = disp_links[0].from_socket
            
            # disconnect the displacement node
            node_tree.links.remove(disp_links[0])
            
            # find out what Surface was connected to
            surf_links = surf_output.links
            if surf_links:
                surf_node_socket = surf_links[0].from_socket
                # disconnect the surface link
                node_tree.links.remove(surf_links[0])
            else:
                surf_node_socket = None
            
            # connect the old displacement output to the surface input
            temp_disp_link = node_tree.links.new(disp_node_socket, surf_output)
            
            """
            # perhaps create a new UV in case the origin overlaps
            """
            
            try:
                # create a new image texture node
                baked_image_node = node_tree.nodes.new('ShaderNodeTexImage')
                
                try:
                    img_name = f"__{obj.name}_{vert_group}_disp__"
                    if img_name in bpy.data.images and bpy.data.images[img_name].is_float and all(r == res for r in bpy.data.images[img_name].size):
                        """Check the image more"""
                        disp_image = bpy.data.images[img_name]
                        create = False
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

                    # attach the image to the texture node
                    baked_image_node.image = disp_image

                    # select the node
                    node_tree.nodes.active = baked_image_node
                    
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
                        disp_texture = bpy.data.textures.new(img_name, type = 'IMAGE')
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
                    print("resetting material settings")
                    node_tree.nodes.remove(baked_image_node)
            except Exception as e:
                raise e
            finally:
                node_tree.links.remove(temp_disp_link)
                if surf_node_socket is not None:
                    node_tree.links.new(surf_node_socket, surf_output)
                #node_tree.links.new(disp_node_socket, disp_output)
                print("finished resetting material settings")
            


def displace_selected(context, resolution: int, inplace=False):
    if context.scene.render.engine != "CYCLES":
        raise Exception("Cycles must be enabled")
    
    selected = [obj.name for obj in context.selected_objects]
    active_name = context.view_layer.objects.active.name
    
    # for each selected model
    for obj in context.selected_objects:
        if obj.type == "MESH":
            try:
                displace(context, obj, resolution, inplace)
            except:
                traceback.print_exc()
        
    # select the originally selected model
    context.view_layer.objects.active = bpy.data.objects[active_name]
    for obj_name in selected:
        bpy.data.objects[obj_name]
        obj.select_set(True) 

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


bl_info = {
    "name": "Move X Axis",
    "blender": (2, 80, 0),
    "category": "Object",
}


class DisplaceIt(bpy.types.Operator):
    """Convert Shader Displacement to Mesh Displacement."""
    bl_idname = "object.displace_it"
    bl_label = "DisplaceIt"
    bl_options = {'REGISTER', 'UNDO'}
    
    inplace: bpy.props.BoolProperty(name="Inplace")
    res: bpy.props.IntProperty(name="Resolution", default=512, min=128, max=65536)

    def execute(self, context):
        displace_selected(context, self.res, self.inplace)
        return {'FINISHED'}
    
def menu_func(self, context):
    self.layout.operator(DisplaceIt.bl_idname)

def register():
    bpy.utils.register_class(DisplaceIt)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.utils.unregister_class(DisplaceIt)
    bpy.types.VIEW3D_MT_object.remove(menu_func)


if __name__ == "__main__":
    register()
