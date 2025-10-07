import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import mysql.connector
from werkzeug.utils import secure_filename
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Upload config
UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


mydb = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST", "mysql-startoys.alwaysdata.net"),
    user=os.getenv("MYSQL_USER", "startoys"),
    password=os.getenv("MYSQL_PASSWORD", "Nicholas1105"),
    database=os.getenv("MYSQL_DB", "startoys_db"),
    port=3306
)

def process_image(file, filename):
    """Resize and compress image before saving."""
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    img = Image.open(file)
    img.thumbnail((400, 400))
    img.save(filepath, optimize=True, quality=80)
    return f"/static/uploads/{filename}"


# def get_connection():
#     return mysql.connector.connect(
#         host=os.environ.get("MYSQLHOST", "mysql-startoys.alwaysdata.net"),
#         user=os.environ.get("MYSQLUSER", "startoys"),
#         password=os.environ.get("MYSQLPASSWORD", "Nicholas1105"),
#         database=os.environ.get("MYSQLDATABASE", "startoys_db")
#         port=3306
#     )


# -------------------- INVENTORY --------------------
@app.route("/", methods=["GET"])
def home():
    search_term = request.args.get("q", "").strip()
    conn = mydb
    cursor = conn.cursor(dictionary=True)
    if search_term:
        like = f"%{search_term}%"
        cursor.execute("""
            SELECT * FROM inventory
            WHERE product_id LIKE %s OR name LIKE %s OR supplier LIKE %s
        """, (like, like, like))
    else:
        cursor.execute("SELECT * FROM inventory")
    rows = cursor.fetchall()
    conn.close()
    return render_template("index.html", rows=rows, search=search_term)


# -------------------- ADD PRODUCT --------------------
@app.route("/add", methods=["POST"])
def add():
    product_id = request.form["product_id"]
    name = request.form["name"]
    stock = int(request.form["stock"] or 0)
    supplier = request.form.get("supplier")
    cost_price = float(request.form["cost_price"] or 0)
    selling_price = float(request.form["selling_price"] or 0)

    image_url = None
    if "image_file" in request.files:
        file = request.files["image_file"]
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            image_url = process_image(file, filename)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inventory (product_id, name, stock, image_url, supplier, cost_price, selling_price)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (product_id, name, stock, image_url, supplier, cost_price, selling_price))
    conn.commit()
    conn.close()
    return redirect(url_for("home"))


# -------------------- DELETE PRODUCT --------------------
@app.route("/delete/<int:item_id>")
def delete(item_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventory WHERE id=%s", (item_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("home"))


# -------------------- INVOICE CREATION --------------------
@app.route("/invoice")
def invoice():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM inventory")
    rows = cursor.fetchall()
    conn.close()
    return render_template("invoice.html", rows=rows)


@app.route("/save_invoice", methods=["POST"])
def save_invoice():
    try:
        data = request.get_json(force=True)
        customer_name = (data.get("customer_name") or "").strip()
        items = data.get("items", [])
        if not customer_name:
            return jsonify({"error": "Customer name is required."}), 400
        if not items:
            return jsonify({"error": "No items to save."}), 400

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("INSERT INTO invoices (customer_name) VALUES (%s)", (customer_name,))
        invoice_id = cursor.lastrowid

        for item in items:
            product_id = item.get("id")
            qty = int(item.get("qty", 0))
            price = float(item.get("price", 0))
            subtotal = qty * price

            cursor.execute("""
                INSERT INTO invoice_items (invoice_id, product_id, quantity, price, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (invoice_id, product_id, qty, price, subtotal))

            cursor.execute("""
                UPDATE inventory SET stock = stock - %s WHERE id = %s AND stock >= %s
            """, (qty, product_id, qty))
            if cursor.rowcount == 0:
                conn.rollback()
                cursor.execute("SELECT name, stock FROM inventory WHERE id=%s", (product_id,))
                p = cursor.fetchone()
                return jsonify({"error": f"Not enough stock for {p['name']} (Stock: {p['stock']})."}), 400

        conn.commit()
        return jsonify({"message": "Invoice created", "invoice_id": invoice_id}), 200

    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals() and conn.is_connected(): conn.close()


# -------------------- INVOICES LIST --------------------
@app.route("/invoices")
def invoices():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT i.id, i.customer_name, i.created_at, SUM(ii.subtotal) AS total
        FROM invoices i
        LEFT JOIN invoice_items ii ON i.id = ii.invoice_id
        GROUP BY i.id
        ORDER BY i.created_at DESC
    """)
    data = cursor.fetchall()
    conn.close()
    return render_template("invoices.html", invoices=data)


# -------------------- INVOICE DETAIL --------------------
@app.route("/invoice/<int:invoice_id>")
def invoice_detail(invoice_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM invoices WHERE id=%s", (invoice_id,))
    invoice = cursor.fetchone()
    cursor.execute("""
        SELECT ii.*, inv.name, inv.image_url
        FROM invoice_items ii
        JOIN inventory inv ON ii.product_id = inv.id
        WHERE ii.invoice_id=%s
    """, (invoice_id,))
    items = cursor.fetchall()
    total = sum(float(i["subtotal"]) for i in items)
    conn.close()
    return render_template("invoice_detail.html", invoice=invoice, items=items, total=total)


# -------------------- DELETE INVOICE --------------------
@app.route("/invoice/<int:invoice_id>/delete", methods=["POST"])
def invoice_delete(invoice_id):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT product_id, quantity FROM invoice_items WHERE invoice_id=%s", (invoice_id,))
        items = cursor.fetchall()
        for it in items:
            cursor.execute("UPDATE inventory SET stock = stock + %s WHERE id=%s", (it["quantity"], it["product_id"]))
        cursor.execute("DELETE FROM invoices WHERE id=%s", (invoice_id,))
        conn.commit()
        return jsonify({"message": "Invoice deleted and stock restored."}), 200
    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals() and conn.is_connected(): conn.close()


# -------------------- 🔹 INVOICE EDIT MODAL (MAIN CHANGE AREA) --------------------
@app.route("/invoice/<int:invoice_id>/edit_modal", methods=["POST"])
def invoice_edit_modal(invoice_id):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # 🔹 Update customer name
        customer_name = request.form.get("customer_name")
        cursor.execute("UPDATE invoices SET customer_name=%s WHERE id=%s", (customer_name, invoice_id))

        # 🔹 Parse submitted item data
        item_ids = request.form.getlist("item_id")
        quantities = request.form.getlist("quantity")
        prices = request.form.getlist("price")

        # 🔹 Get current items from DB
        cursor.execute("""
            SELECT ii.id AS item_id, ii.product_id, ii.quantity
            FROM invoice_items ii
            WHERE ii.invoice_id=%s
        """, (invoice_id,))
        current_items = {str(row["item_id"]): row for row in cursor.fetchall()}

        seen_ids = []

        # 🔹 Update or adjust quantities
        for i in range(len(item_ids)):
            item_id = str(item_ids[i])
            if item_id not in current_items:
                continue

            product_id = current_items[item_id]["product_id"]
            old_qty = current_items[item_id]["quantity"]
            new_qty = int(quantities[i])
            price = float(prices[i])
            diff = new_qty - old_qty

            if diff > 0:
                cursor.execute("UPDATE inventory SET stock = stock - %s WHERE id=%s AND stock >= %s",
                               (diff, product_id, diff))
                if cursor.rowcount == 0:
                    conn.rollback()
                    return jsonify({"error": f"Not enough stock for product ID {product_id}."}), 400
            elif diff < 0:
                cursor.execute("UPDATE inventory SET stock = stock + %s WHERE id=%s", (-diff, product_id))

            cursor.execute("""
                UPDATE invoice_items
                SET quantity=%s, price=%s, subtotal=%s
                WHERE id=%s
            """, (new_qty, price, new_qty * price, item_id))
            seen_ids.append(item_id)

        # 🔹 Delete any removed rows and restore stock
        for existing_id in list(current_items.keys()):
            if existing_id not in seen_ids:
                prod_id = current_items[existing_id]["product_id"]
                qty_restore = current_items[existing_id]["quantity"]
                cursor.execute("UPDATE inventory SET stock = stock + %s WHERE id=%s", (qty_restore, prod_id))
                cursor.execute("DELETE FROM invoice_items WHERE id=%s", (existing_id,))

        # 🔹 Delete entire invoice if empty
        cursor.execute("SELECT COUNT(*) AS cnt FROM invoice_items WHERE invoice_id=%s", (invoice_id,))
        count = cursor.fetchone()["cnt"]
        if count == 0:
            cursor.execute("DELETE FROM invoices WHERE id=%s", (invoice_id,))
            conn.commit()
            return jsonify({"message": "Invoice deleted since no items remain."}), 200

        conn.commit()
        return jsonify({"message": "Invoice updated successfully"}), 200

    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals() and conn.is_connected(): conn.close()
# -------------------- 🔹 END OF MODAL EDIT LOGIC --------------------

@app.route("/invoice/<int:invoice_id>/pdf")
def invoice_pdf(invoice_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch invoice header
    cursor.execute("SELECT * FROM invoices WHERE id=%s", (invoice_id,))
    invoice = cursor.fetchone()

    # Fetch invoice items
    cursor.execute("""
        SELECT ii.*, inv.name, inv.image_url 
        FROM invoice_items ii
        JOIN inventory inv ON ii.product_id = inv.id
        WHERE ii.invoice_id=%s
    """, (invoice_id,))
    items = cursor.fetchall()
    conn.close()

    # Create PDF buffer
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 50
    y = height - 50

    # Header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(margin, y, f"Invoice #{invoice['id']}")
    y -= 30
    p.setFont("Helvetica", 12)
    p.drawString(margin, y, f"Customer: {invoice['customer_name']}")
    y -= 20
    p.drawString(margin, y, f"Date: {invoice['created_at']}")
    y -= 40

    # Table headers
    p.setFont("Helvetica-Bold", 12)
    p.drawString(margin, y, "Qty")
    p.drawString(margin + 40, y, "Product")
    p.drawString(width - 170, y, "Price")
    p.drawString(width - 90, y, "Subtotal")
    y -= 20
    p.line(margin, y, width - margin, y)
    y -= 20

    # Items
    p.setFont("Helvetica", 11)
    total = 0
    for item in items:
        if y < 80:  # Page break safety
            p.showPage()
            y = height - 50
            p.setFont("Helvetica-Bold", 12)
            p.drawString(margin, y, "Qty")
            p.drawString(margin + 40, y, "Product")
            p.drawString(width - 170, y, "Price")
            p.drawString(width - 90, y, "Subtotal")
            y -= 20
            p.line(margin, y, width - margin, y)
            y -= 20
            p.setFont("Helvetica", 11)

        qty = str(item["quantity"])
        name = item["name"] or "Unnamed"
        price = f"${item['price']:.2f}"
        subtotal = f"${item['subtotal']:.2f}"

        # ✅ Truncate product name dynamically if too long
        max_chars = 60  # Adjust depending on your font size / width
        if len(name) > max_chars:
            name = name[:max_chars - 3] + "..."

        p.drawString(margin, y, qty)
        p.drawString(margin + 40, y, name)
        p.drawRightString(width - 100, y, price)
        p.drawRightString(width - 40, y, subtotal)

        total += float(item["subtotal"])
        y -= 20

    # Total
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawRightString(width - 100, y, "TOTAL:")
    p.drawRightString(width - 40, y, f"${total:.2f}")
    

    # Finalize PDF
    p.showPage()
    p.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"invoice_{invoice['id']}.pdf",
        mimetype="application/pdf"
    )


if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)




