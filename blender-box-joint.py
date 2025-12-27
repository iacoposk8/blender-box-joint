import bpy
import bmesh
from mathutils import Vector, Matrix

# --- USER PARAMETERS ---
extra_size = 0.5  # Tolerance: how much larger the cutter tooth is (Clearance)
# -----------------------

def create_complete_box_joint():
    # Object A: The active object we are modifying
    obj_source = bpy.context.active_object
    
    if obj_source is None or obj_source.mode != 'EDIT':
        print("ERROR: You must be in EDIT MODE with a face selected.")
        return

    # Access mesh data
    bm = bmesh.from_edit_mesh(obj_source.data)
    selected_faces = [f for f in bm.faces if f.select]

    if len(selected_faces) != 1:
        print("ERROR: Please select exactly ONE face.")
        return

    face = selected_faces[0]
    mw = obj_source.matrix_world
    
    # --- 1. ADJACENT OBJECT DETECTION (Raycast) ---
    
    # Calculate global center and normal
    face_center = mw @ face.calc_center_median()
    face_normal = (mw.to_3x3() @ face.normal).normalized()
    
    # Prepare the ray: Starts from face center and goes outwards along normal
    # Small offset (0.01) to avoid hitting the source object itself
    ray_origin = face_center + (face_normal * 0.01)
    ray_direction = face_normal
    
    # Cast ray into the scene
    depsgraph = bpy.context.view_layer.depsgraph
    result, loc, norm, idx, obj_target, mat = depsgraph.scene_eval.ray_cast(depsgraph, ray_origin, ray_direction)
    
    if result:
        print(f"Adjacent object found: {obj_target.name}")
    else:
        print("WARNING: No adjacent object found along the normal!")
        obj_target = None

    # --- 2. GEOMETRY ANALYSIS (World Space) ---
    v_edges = []
    for edge in face.edges:
        p1 = mw @ edge.verts[0].co
        p2 = mw @ edge.verts[1].co
        vec = p2 - p1
        v_edges.append((vec.length, vec))
    
    # Sort edges by length (descending)
    v_edges.sort(key=lambda x: x[0], reverse=True)
    
    long_edge_len = v_edges[0][0]
    long_edge_vec = v_edges[0][1]
    short_edge_len = v_edges[-1][0]
    
    # Calculate Tooth Dimensions
    dim_width = long_edge_len / 2.0   # Half of the long side
    dim_thick = short_edge_len        # Full thickness of the short side
    dim_protrusion = dim_thick        # Protrusion equals thickness

    # --- 3. ORIENTATION CALCULATION ---
    face_tangent = long_edge_vec.normalized()
    face_binormal = face_normal.cross(face_tangent).normalized()
    
    # Rotation matrix based on the face orientation
    rot_matrix = Matrix((face_tangent, face_binormal, face_normal)).transposed().to_4x4()
    
    # Final position: face center + moved outwards by half protrusion
    final_location = face_center + (face_normal * (dim_protrusion / 2))
    rot_matrix.translation = final_location

    # --- 4. CREATE HELPER OBJECTS ---
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Manage Collection
    col_name = "BoxJoint_Helpers"
    if col_name not in bpy.data.collections:
        col = bpy.data.collections.new(col_name)
        bpy.context.scene.collection.children.link(col)
    else:
        col = bpy.data.collections[col_name]
    
    # >>> HIDE THE COLLECTION FROM VIEWPORT <<<
    col.hide_viewport = True

    # Internal helper function to create cubes
    def create_cube(name, size_vec):
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)
        col.objects.link(obj) # Link to the hidden collection
        
        bm_temp = bmesh.new()
        bmesh.ops.create_cube(bm_temp, size=1.0)
        bm_temp.to_mesh(mesh)
        bm_temp.free()
        
        obj.matrix_world = rot_matrix
        obj.scale = size_vec
        
        # Set to wireframe just in case the collection is unhidden later
        obj.display_type = 'WIRE'
        
        return obj

    # Create Union Tooth (Exact size)
    tooth_union = create_cube("Tooth_Union", 
                            (dim_width, dim_thick, dim_protrusion))

    # Create Cutter Tooth (Larger size for clearance)
    tooth_cutter = create_cube("Tooth_Cutter", 
                            (dim_width + extra_size, dim_thick + extra_size, dim_protrusion + extra_size))

    # --- 5. APPLY BOOLEAN MODIFIERS ---
    
    # Union Modifier on Source Object
    mod_union = obj_source.modifiers.new(name="Joint_Union", type='BOOLEAN')
    mod_union.operation = 'UNION'
    mod_union.object = tooth_union
    mod_union.solver = 'FAST' # 'FAST' is often better for simple geometry
    
    # Difference Modifier on Target (Adjacent) Object
    if obj_target:
        mod_diff = obj_target.modifiers.new(name="Joint_Cut", type='BOOLEAN')
        mod_diff.operation = 'DIFFERENCE'
        mod_diff.object = tooth_cutter
        mod_diff.solver = 'FAST'
        print(f"Modifiers applied to {obj_source.name} and {obj_target.name}")
    
    # Update view and re-select the main object
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    obj_source.select_set(True)
    bpy.context.view_layer.objects.active = obj_source
    
    print("Operation complete. Helper collection created and hidden.")

# Run the script
create_complete_box_joint()
