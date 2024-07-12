import os


def rename_images(directory):
    # 获取目录下所有文件名
    files = os.listdir(directory)

    # 过滤出图片文件（假设只处理常见的图片格式，如jpg、png等）
    image_files = [f for f in files if f.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif'))]

    # 排序图片文件，确保按照顺序命名
    image_files.sort()

    # 逐个重命名图片文件
    for i, filename in enumerate(image_files):
        extension = os.path.splitext(filename)[1]  # 获取文件扩展名
        new_filename = f"{i + 1}{extension}"  # 新文件名，例如 image_1.jpg
        os.rename(os.path.join(directory, filename), os.path.join(directory, new_filename))
        print(f"Renamed {filename} to {new_filename}")


# 调用函数并传入目录路径
if __name__ == "__main__":
    directory_path = "C:\\Users\\23231\\Desktop\\sc"
    rename_images(directory_path)
