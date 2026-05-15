import os
import xml.etree.ElementTree as ET

# ==========================================
# 1. CONFIGURATION
# ==========================================
CLASSES = ["trash"]  # This must match the <name> tag in your XML

# ==========================================
# 2. HELPER: MATH CONVERSION
# ==========================================
def convert_to_yolo(size, box):
    """Normalizes coordinates to [0, 1] for YOLO."""
    dw = 1. / size[0]
    dh = 1. / size[1]
    x = (box[0] + box[1]) / 2.0
    y = (box[2] + box[3]) / 2.0
    w = box[1] - box[0]
    h = box[3] - box[2]
    return (x * dw, y * dh, w * dw, h * dh)

# ==========================================
# 3. MAIN LOGIC: FOLDER PROCESSING
# ==========================================
def process_folder(xml_dir, output_txt_dir):
    """Reads XMLs from xml_dir and saves TXTs to output_txt_dir."""
    if not os.path.exists(output_txt_dir):
        os.makedirs(output_txt_dir)
        print(f"Created directory: {output_txt_dir}")

    count = 0
    for xml_file in os.listdir(xml_dir):
        if not xml_file.endswith('.xml'):
            continue
        
        try:
            tree = ET.parse(os.path.join(xml_dir, xml_file))
            root = tree.getroot()
            
            # Get image dimensions
            img_w = int(root.find('size/width').text)
            img_h = int(root.find('size/height').text)

            yolo_data = []
            for obj in root.findall('object'):
                cls_name = obj.find('name').text
                if cls_name not in CLASSES:
                    continue
                
                cls_id = CLASSES.index(cls_name)
                xmlbox = obj.find('bndbox')
                
                # Get pixel coordinates
                b = (float(xmlbox.find('xmin').text), 
                     float(xmlbox.find('xmax').text), 
                     float(xmlbox.find('ymin').text), 
                     float(xmlbox.find('ymax').text))
                
                # Convert to YOLO format
                bb = convert_to_yolo((img_w, img_h), b)
                yolo_data.append(f"{cls_id} {' '.join([f'{coord:.6f}' for coord in bb])}")

            # Save the .txt file
            txt_filename = xml_file.replace('.xml', '.txt')
            with open(os.path.join(output_txt_dir, txt_filename), 'w') as f:
                f.write('\n'.join(yolo_data))
            count += 1
        except Exception as e:
            print(f"Error processing {xml_file}: {e}")

    print(f"Finished! Processed {count} files in {xml_dir}")

# ==========================================
# 4. EXECUTION
# ==========================================
if __name__ == "__main__":
    # Base path is current folder/trashSet
    base_path = "./trashSet"

    # Define source XML folders
    train_xml_dir = os.path.join(base_path, "annotation", "trashAnnotatedTrain")
    test_xml_dir = os.path.join(base_path, "annotation", "trashAnnotatedtest")

    # Define destination Label folders
    train_output_dir = "./dataset/train/labels"
    test_output_dir = "./dataset/val/labels"

    # Run the processing for Train
    if os.path.exists(train_xml_dir):
        print(f"Starting conversion for Train...")
        process_folder(train_xml_dir, train_output_dir)
    else:
        print(f"ERROR: Could not find {train_xml_dir}")

    # Run the processing for Test
    if os.path.exists(test_xml_dir):
        print(f"Starting conversion for Test...")
        process_folder(test_xml_dir, test_output_dir)
    else:
        print(f"ERROR: Could not find {test_xml_dir}")