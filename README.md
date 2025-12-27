# Blender Auto Box Joint Generator

A smart Blender Python script to instantly create **Box Joints** (also known as **Finger Joints** or **Comb Joints**) between two adjacent objects.

Designed for **3D Printing**, **CNC**, and **Laser Cut** workflows, this tool automates the tedious process of measuring, aligning, and applying boolean operations for joinery.

## 🚀 Features

*   **Smart Dimension Detection:** Automatically calculates tooth width and thickness based on the selected face geometry (World Space).
*   **Auto-Alignment:** Aligns the tooth orientation perfectly with the face normal and tangent.
*   **Adjacent Object Detection:** Uses Raycasting to automatically find the object touching the selected face.
*   **Automatic Booleans:**
    *   Applies a **Union** modifier to the source object.
    *   Applies a **Difference** modifier to the adjacent object.
*   **Tolerance Control:** Includes a configurable `extra_size` parameter to create clearance (kerf/offset), ensuring parts fit together in the real world.
*   **Non-Destructive:** Uses modifiers and keeps helper geometry in a hidden collection (`BoxJoint_Helpers`), keeping your viewport clean.

## 🛠️ Installation

1.  Download the `.py` script from this repository.
2.  Open Blender.
3.  Go to the **Scripting** tab.
4.  Click **New** or **Open** and load the script.
5.  (Optional) You can save this in your startup file or turn it into a button if you are familiar with Blender API.

## 📖 Usage

1.  **Position your objects:** Ensure your two objects (e.g., two wooden planks) are touching or intersecting where you want the joint.
2.  **Select the Source Object:** Click the object where you want to add the "male" tooth.
3.  **Enter Edit Mode:** Press `Tab`.
4.  **Select the Face:** Select the single face that touches the adjacent object.
5.  **Run the Script:** Click the "Play" icon in the Text Editor.

**Result:**
*   The script adds the tooth to your selected object.
*   It cuts a slightly larger hole (based on tolerance) into the adjacent object.
*   The helper objects are hidden automatically.

## ⚙️ Configuration

Open the script in the Text Editor and look for the **User Parameters** section at the top:

```python
# --- USER PARAMETERS ---
extra_size = 1.0  # Tolerance: how much larger the cutter tooth is
# -----------------------
```

*   **extra_size:** Defines the clearance/tolerance.
    *   Value is in Blender Units (usually meters or millimeters depending on your scene settings).
    *   Increase this value for **CNC** routing to account for bit radius or for **3D printing** to ensure a loose fit.
    *   Set to `0.0` for a zero-tolerance interference fit.

## 🎯 Ideal For

*   **Woodworking:** Designing joinery for furniture.
*   **CNC Routers:** Creating dog-bone style or standard box joints.
*   **Laser Cutting:** Prototyping boxes and enclosures with **Finger Joints**.
*   **3D Printing:** Creating split parts that snap together.

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

[MIT](https://choosealicense.com/licenses/mit/)
