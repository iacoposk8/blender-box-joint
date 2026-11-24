"""In Edit Mode selezionare una faccia rettangolare sul bordo del pannello.
Crea un dente centrale e la sua sede con modificatori non distruttivi.
Le misure sono in unita Blender (nel progetto solderStation: millimetri).
Non compensa il raggio fresa: dog-bone e percorsi utensile vanno gestiti nel CAM.
"""
import math

import bpy
import bmesh
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

extra_size = 0.5  # Gioco TOTALE: 0.25 per lato, non 0.5 per lato.
HELPER_COLLECTION = "BoxJoint_Helpers"


def _face_geometry(obj, face):
    if len(face.verts) != 4:
        raise ValueError("Seleziona una faccia rettangolare con quattro vertici.")
    mw = obj.matrix_world
    points = [mw @ v.co for v in face.verts]
    edges = [points[(i + 1) % 4] - points[i] for i in range(4)]
    if min(e.length for e in edges) <= 1e-8:
        raise ValueError("La faccia contiene spigoli degeneri.")
    for i, edge in enumerate(edges):
        if abs(edge.normalized().dot(edges[(i + 1) % 4].normalized())) > 1e-4:
            raise ValueError("La faccia deve essere rettangolare anche nello spazio globale.")
    # Inversa trasposta: corretta anche con scale non uniformi.
    normal = (mw.to_3x3().inverted().transposed() @ face.normal).normalized()
    tangent = max(edges, key=lambda e: e.length).normalized()
    binormal = normal.cross(tangent).normalized()
    if any(abs((p - points[0]).dot(normal)) > max(e.length for e in edges) * 1e-5
           for p in points):
        raise ValueError("La faccia non e planare.")
    return (sum(points, Vector()) / 4, normal, tangent, binormal,
            max(e.length for e in edges) / 2, min(e.length for e in edges))


def _target_candidates(source, center, normal, tangent, binormal, width, thickness):
    """Raggi in world space sui soli pannelli, non sui denti ausiliari.

    Partono PRIMA del contatto: partire oltre la faccia puo saltare una
    superficie coincidente. Nove campioni evitano di dipendere dal solo centro.
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    epsilon = max(thickness * 1e-4, 1e-6)
    candidates = []
    for obj in bpy.context.visible_objects:
        if obj == source or obj.type != 'MESH':
            continue
        if obj.get("box_joint_helper") or any(c.name == HELPER_COLLECTION for c in obj.users_collection):
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            vertices = [evaluated.matrix_world @ v.co for v in mesh.vertices]
            polygons = [tuple(p.vertices) for p in mesh.polygons]
            if not polygons:
                continue
            tree = BVHTree.FromPolygons(vertices, polygons)
            hits = 0
            for u in (-0.4, 0.0, 0.4):
                for v in (-0.4, 0.0, 0.4):
                    origin = (center + tangent * (u * width)
                              + binormal * (v * thickness) - normal * epsilon)
                    location, _, _, distance = tree.ray_cast(origin, normal, thickness + 2 * epsilon)
                    if location is not None and distance <= thickness + 2 * epsilon:
                        hits += 1
            if hits:
                candidates.append(obj)
        finally:
            evaluated.to_mesh_clear()
    return candidates


def create_complete_box_joint(target_name=None):
    """target_name opzionale risolve esplicitamente contatti con piu pannelli."""
    source = bpy.context.active_object
    if source is None or source.type != 'MESH' or source.mode != 'EDIT':
        print("ERRORE: entra in Edit Mode e seleziona UNA faccia di bordo.")
        return False
    if not math.isfinite(extra_size) or extra_size < 0:
        print("ERRORE: extra_size deve essere finito e non negativo.")
        return False
    bm = bmesh.from_edit_mesh(source.data)
    bm.normal_update()
    faces = [f for f in bm.faces if f.select]
    if len(faces) != 1:
        print("ERRORE: seleziona esattamente UNA faccia.")
        return False
    try:
        center, normal, tangent, binormal, width, thickness = _face_geometry(source, faces[0])
    except (ValueError, ZeroDivisionError) as error:
        print(f"ERRORE: {error}")
        return False

    # Sincronizza la geometria prima di interrogare la scena valutata.
    bpy.ops.object.mode_set(mode='OBJECT')
    helpers, modifiers = [], []
    try:
        bpy.context.view_layer.update()
        candidates = _target_candidates(source, center, normal, tangent, binormal, width, thickness)
        if target_name is not None:
            candidates = [obj for obj in candidates if obj.name == target_name]
        if len(candidates) != 1:
            names = ', '.join(obj.name for obj in candidates) or 'nessuno'
            raise ValueError(f"Pannello adiacente non univoco ({names}). "
                             "Controlla la faccia/normale oppure specifica target_name. Nessun incastro creato.")
        target = candidates[0]
        collection = bpy.data.collections.get(HELPER_COLLECTION)
        if collection is None:
            collection = bpy.data.collections.new(HELPER_COLLECTION)
            bpy.context.scene.collection.children.link(collection)
        # Non escludere la collection dal depsgraph: i Boolean devono valutarla.
        collection.hide_viewport = False
        overlap = max(thickness * 1e-3, 1e-5)
        rotation = Matrix((tangent, binormal, normal)).transposed().to_4x4()
        rotation.translation = center + normal * ((thickness - overlap) / 2)

        def create_cube(name, dimensions):
            mesh = bpy.data.meshes.new(name)
            obj = bpy.data.objects.new(name, mesh)
            collection.objects.link(obj)
            helpers.append(obj)
            temp = bmesh.new()
            try:
                bmesh.ops.create_cube(temp, size=1.0)
                # Dimensioni nella mesh: niente scale non uniformi sui cutter.
                for vertex in temp.verts:
                    for axis in range(3):
                        vertex.co[axis] *= dimensions[axis]
                temp.to_mesh(mesh)
            finally:
                temp.free()
            obj.matrix_world = rotation
            obj["box_joint_helper"] = True
            obj.display_type = 'WIRE'
            obj.hide_render = True
            obj.hide_set(True)
            return obj

        tooth = create_cube("Tooth_Union", (width, thickness, thickness + overlap))
        cutter = create_cube("Tooth_Cutter", (width + extra_size, thickness + extra_size,
                                              thickness + overlap + extra_size))
        for obj, operation, helper, name in (
                (source, 'UNION', tooth, "Joint_Union"),
                (target, 'DIFFERENCE', cutter, "Joint_Cut")):
            modifier = obj.modifiers.new(name=name, type='BOOLEAN')
            modifiers.append((obj, modifier))
            modifier.operation = operation
            modifier.object = helper
            modifier.solver = 'EXACT'
        bpy.context.view_layer.update()
        print(f"Incastro creato: {source.name} -> {target.name} (gioco totale {extra_size:g}).")
        return True
    except Exception as error:
        # Non lasciare un mezzo incastro o cutter orfani in caso di errore.
        for obj, modifier in reversed(modifiers):
            obj.modifiers.remove(modifier)
        for obj in reversed(helpers):
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        print(f"ERRORE: {error}")
        return False
    finally:
        bpy.context.view_layer.objects.active = source
        source.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')


if __name__ == "__main__":
    create_complete_box_joint()
