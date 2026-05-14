# hashing_logic.py

from PIL import Image
import imagehash
import os
import json

# File where hashes are stored
HASH_DATABASE = "image_hashes.json"

# Threshold:
# Smaller number = stricter duplicate detection
# Recommended: 5 to 10
SIMILARITY_THRESHOLD = 6


def load_hashes():
    """
    Load previously stored image hashes
    """
    if not os.path.exists(HASH_DATABASE):
        return []

    with open(HASH_DATABASE, "r") as file:
        return json.load(file)


def save_hashes(hash_list):
    """
    Save image hashes to file
    """
    with open(HASH_DATABASE, "w") as file:
        json.dump(hash_list, file)


def generate_image_hash(image_path):
    """
    Generate perceptual hash of image
    """
    image = Image.open(image_path)

    # Resize + pixel comparison style hashing
    hash_value = imagehash.phash(image)

    return str(hash_value)


def is_duplicate(new_hash, existing_hashes):
    """
    Compare uploaded image hash with stored hashes
    """

    new_hash_obj = imagehash.hex_to_hash(new_hash)

    for old_hash in existing_hashes:
        old_hash_obj = imagehash.hex_to_hash(old_hash)

        # Hamming distance between hashes
        difference = new_hash_obj - old_hash_obj

        print(f"Comparing hashes | Difference: {difference}")

        # If difference is small, images are very similar
        if difference <= SIMILARITY_THRESHOLD:
            return True

    return False


def validate_image(image_path):
    """
    Main function to validate uploaded image
    """

    existing_hashes = load_hashes()

    new_hash = generate_image_hash(image_path)

    if is_duplicate(new_hash, existing_hashes):
        return {
            "status": "REJECTED",
            "message": "Duplicate image detected. No points awarded."
        }

    # Save new unique image hash
    existing_hashes.append(new_hash)
    save_hashes(existing_hashes)

    return {
        "status": "APPROVED",
        "message": "Image accepted. Points can be awarded."
    }


# Example testing
if __name__ == "__main__":

    image_path = input("Enter image path: ")

    result = validate_image(image_path)

    print(result)
