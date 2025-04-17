import os
import cv2
import sys
from jinja2 import Template
from PIL import Image
from analyze import get_sell_points_from_all_images, classify_image_by_points

SOURCE_DIR = "images"
OUTPUT_DIR = "subimages"
RESULT_HTML = "result.html"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def join_images_vertically(image_paths, save_path):
    if not image_paths:
        return None
    images = [Image.open(p) for p in image_paths if os.path.exists(p)]
    if not images:
        return None
    widths = [img.width for img in images]
    heights = [img.height for img in images]
    total_height = sum(heights)
    max_width = max(widths)
    new_img = Image.new('RGB', (max_width, total_height), (255, 255, 255))
    y_offset = 0
    for img in images:
        new_img.paste(img, (0, y_offset))
        y_offset += img.height
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    new_img.save(save_path)
    return save_path

def split_image(image_path, output_dir, min_gap=10, black_threshold=30, min_height=60):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    row_mean = gray.mean(axis=1)
    is_black = row_mean < black_threshold
    black_bands = []
    start = None
    for i, val in enumerate(is_black):
        if val:
            if start is None:
                start = i
        else:
            if start is not None and i - start > min_gap:
                black_bands.append((start, i))
                start = None
    if start is not None and gray.shape[0] - start > min_gap:
        black_bands.append((start, gray.shape[0]))
    split_points = [0] + [int((a + b) / 2) for a, b in black_bands] + [img.shape[0]]
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    sub_images = []
    for i in range(len(split_points) - 1):
        y1, y2 = split_points[i], split_points[i + 1]
        if y2 - y1 < min_height:
            continue
        crop = img[y1:y2, :]
        sub_name = f"{base_name}_{i}.jpg"
        sub_path = os.path.join(output_dir, sub_name)
        cv2.imwrite(sub_path, crop)
        sub_images.append(sub_path)
    return sub_images

def generate_html(table_data, output_file):

    # 命中统计 + 卖点排序

    point_counts = {pt: 0 for pt in table_data["points"]}

    for pt in table_data["points"]:

        for row in table_data["table"]:

            if row["points"].get(pt):

                point_counts[pt] += 1

    sorted_points = sorted(table_data["points"], key=lambda p: -point_counts[p])



    html_template = """

    <html>

    <head>

        <meta charset='utf-8'>

        <style>

            body { font-family: Arial, sans-serif; }

            .table-wrapper {

                overflow-x: auto;

                max-width: 100%;

                border: 1px solid #ddd;

            }

            table {

                border-collapse: collapse;

                min-width: 1200px;

            }

            th, td {

                border: 1px solid #ccc;

                padding: 10px;

                text-align: center;

                vertical-align: top;

                white-space: nowrap;

            }

            img.thumb {

                width: 120px;

                height: 120px;

                object-fit: contain;

                cursor: zoom-in;

                transition: transform 0.2s ease;

            }

            .xmark {

                color: #e74c3c;

                font-size: 20px;

                font-weight: bold;

            }



            /* 固定列样式 */

            th.sticky, td.sticky {

                position: sticky;

                left: 0;

                background-color: #f9f9f9;

                z-index: 1;

            }

            td.sticky-2, th.sticky-2 {

                position: sticky;

                left: 120px;

                background-color: #f9f9f9;

                z-index: 1;

            }



            /* Modal 样式 */

            .modal {

                display: none;

                position: fixed;

                z-index: 9999;

                left: 0; top: 0;

                width: 100%; height: 100%;

                background-color: rgba(0,0,0,0.8);

                overflow: hidden;

                cursor: grab;

            }

            .modal-content {

                position: absolute;

                top: 50%;

                left: 50%;

                max-width: none;

                transform: translate(-50%, -50%) scale(1);

                transform-origin: center center;

            }

            .modal-close {

                position: absolute;

                top: 20px; right: 40px;

                font-size: 40px;

                color: white;

                cursor: pointer;

                z-index: 99999;

            }

        </style>

    </head>

    <body>

        <h2>🧠 商品卖点对比分析图</h2>

        <div class="table-wrapper">

        <table>

            <thead>

                <tr>

                    <th class="sticky">卖点</th >

                    <th class="sticky-2">命中数</th>

                    {% for row in table %}

                    <th><a href="https://www.amazon.com/dp/{{ row.product }}" target="_blank">{{ row.product }}</a></th>

                    {% endfor %}

                </tr>

            </thead>

            <tbody>

                {% for pt in points %}

                <tr>

                    <td class="sticky">{{ pt }}</td>

                    <td class="sticky-2"><strong>{{ counts[pt] }}</strong></td>

                    {% for row in table %}

                    <td>

                        {% if row.points[pt] %}

                        <img class="thumb" src="{{ row.points[pt] }}" onclick="showModal(this.src)" />

                        {% else %}

                        <span class="xmark">❌</span>

                        {% endif %}

                    </td>

                    {% endfor %}

                </tr>

                {% endfor %}

            </tbody>

        </table>

        </div>



        <!-- Modal 放大图 -->

        <div id="imgModal" class="modal" onmousedown="startDrag(event)" onmouseup="stopDrag()" onmousemove="doDrag(event)">

            <span class="modal-close" onclick="hideModal()">×</span>

            <img class="modal-content" id="modalImage">

        </div>



        <script>
const modal = document.getElementById("imgModal");
const modalImg = document.getElementById("modalImage");

let scale = 1;
let dragging = false;
let startX = 0, startY = 0;
let offsetX = 0, offsetY = 0;

function showModal(src) {
    modal.style.display = "block";
    modalImg.src = src;
    scale = 1;
    offsetX = 0;
    offsetY = 0;
    updateTransform();
}

function hideModal() {
    modal.style.display = "none";
}

function updateTransform() {
    modalImg.style.transform = `translate(-50%, -50%) translate(${offsetX}px, ${offsetY}px) scale(${scale})`;
}

// ✅ 鼠标滚轮缩放
modalImg.addEventListener("wheel", function(event) {
    event.preventDefault();
    scale *= (event.deltaY < 0) ? 1.1 : 0.9;
    updateTransform();
});

// ✅ 鼠标拖动图片本身
modalImg.addEventListener("mousedown", function(e) {
    e.preventDefault();
    dragging = true;
    startX = e.clientX;
    startY = e.clientY;
    modal.style.cursor = "grabbing";
});

window.addEventListener("mouseup", function() {
    dragging = false;
    modal.style.cursor = "grab";
});

window.addEventListener("mousemove", function(e) {
    if (!dragging) return;
    offsetX += e.clientX - startX;
    offsetY += e.clientY - startY;
    startX = e.clientX;
    startY = e.clientY;
    updateTransform();
});
</script>

    </body>

    </html>

    """

    template = Template(html_template)

    with open(output_file, "w", encoding="utf-8") as f:

        f.write(template.render(

            table=table_data["table"],

            points=sorted_points,

            counts=point_counts

        ))

def main():
    if len(sys.argv) < 2:
        print("❌ 请提供要分析的商品类别，如：python main.py scissors")
        return

    category = sys.argv[1]
    category_path = os.path.join(SOURCE_DIR, category)

    if not os.path.isdir(category_path):
        print(f"❌ 未找到目录：{category_path}")
        return

    image_files = [f for f in os.listdir(category_path) if f.lower().endswith(".jpg")]
    image_paths = [os.path.join(category_path, f) for f in image_files]
    all_products = [os.path.splitext(f)[0] for f in image_files]

    sell_points = get_sell_points_from_all_images(image_paths)
    print(f"🧠 [{category}] 总体识别维度：{sell_points}")

    all_data = []
    for image_file, product_name in zip(image_files, all_products):
        full_path = os.path.join(category_path, image_file)
        sub_images = split_image(full_path, OUTPUT_DIR)
        point_to_subimgs = {pt: [] for pt in sell_points}

        for sub_img in sub_images:
            matched_pts = classify_image_by_points(sub_img, sell_points)
            print(f"  {os.path.basename(sub_img)} ➜ {matched_pts}")
            for pt in matched_pts:
                point_to_subimgs[pt].append(sub_img)

        row = {"product": product_name, "points": {}}
        for pt in sell_points:
            if point_to_subimgs[pt]:
                save_path = os.path.join("joined_images", f"{product_name}_{pt}.jpg")
                joined = join_images_vertically(point_to_subimgs[pt], save_path)
                row["points"][pt] = joined if joined else None
            else:
                row["points"][pt] = None

        all_data.append(row)

    html_file = f"{category}.html"
    table_data = {"points": sell_points, "table": all_data}
    generate_html(table_data, html_file)
    print(f"✅ [{category}] 分析完成，输出：{html_file}")

if __name__ == "__main__":
    main()