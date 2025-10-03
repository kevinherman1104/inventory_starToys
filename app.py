import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
import mysql.connector
from werkzeug.utils import secure_filename
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask import send_file
import io




app = Flask(__name__)
app.secret_key = "your_secret_key"

# Upload config
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def process_image(file, filename):
    """Resize and compress image before saving."""
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    img = Image.open(file)
    img.thumbnail((400, 400))   # resize (max 400x400)
    img.save(filepath, optimize=True, quality=80)  # compress quality 80
    return f"/static/uploads/{filename}"

# Database connection
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Nicholas1105!",  # change this
        database="inventory_db"
    )

# Home / Read
@app.route("/", methods=["GET"])
def home():
    search_term = request.args.get("q", "").strip()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if search_term:
        like_term = f"%{search_term}%"
        cursor.execute("""
            SELECT * FROM inventory
            WHERE product_id LIKE %s
               OR name LIKE %s
               OR supplier LIKE %s
               OR category LIKE %s
        """, (like_term, like_term, like_term, like_term))
    else:
        cursor.execute("SELECT * FROM inventory")

    rows = cursor.fetchall()
    conn.close()

    # If AJAX (dynamic search), return JSON
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        # make rows JSON-serializable
        for r in rows:
            for k, v in list(r.items()):
                if v is None:
                    r[k] = None
                elif hasattr(v, "isoformat"):
                    r[k] = v.isoformat()
                elif not isinstance(v, (str, int, float, bool)):
                    r[k] = str(v)
        return jsonify(rows)

    # normal page load
    return render_template("index.html", rows=rows, search=search_term)


# Create
@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        print("➡️ POST request received")  # Debug

        product_id = request.form["product_id"]
        name = request.form["name"]
        stock = int(request.form["stock"] or 0)
        category = request.form.get("category")
        supplier = request.form.get("supplier")
        cost_price = float(request.form["cost_price"] or 0)
        selling_price = float(request.form["selling_price"] or 0)

        image_url = None  # disable image for now

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO inventory (product_id, name, stock, image_url, category, supplier, cost_price, selling_price)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (product_id, name, stock, image_url, category, supplier, cost_price, selling_price))
        conn.commit()
        conn.close()
        return redirect(url_for("home"))

    return render_template("add.html")


# Update
@app.route("/edit/<int:item_id>", methods=["GET", "POST"])
def edit(item_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        product_id = request.form["product_id"]
        name = request.form["name"]
        stock = request.form["stock"]
        category = request.form["category"]
        supplier = request.form["supplier"]
        cost_price = request.form["cost_price"]
        selling_price = request.form["selling_price"]

        # Handle image upload
        image_url = request.form.get("existing_image")
        if "image_file" in request.files:
            file = request.files["image_file"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                image_url = process_image(file, filename)

        cursor.execute("""
            UPDATE inventory
            SET product_id=%s, name=%s, stock=%s, image_url=%s, category=%s,
                supplier=%s, cost_price=%s, selling_price=%s
            WHERE id=%s
        """, (product_id, name, stock, image_url, category, supplier, cost_price, selling_price, item_id))
        conn.commit()
        conn.close()
        return redirect(url_for("home"))

    cursor.execute("SELECT * FROM inventory WHERE id=%s", (item_id,))
    item = cursor.fetchone()
    conn.close()
    return render_template("edit.html", item=item)

# Delete
@app.route("/delete/<int:item_id>")
def delete(item_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventory WHERE id=%s", (item_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("home"))

#invoice func
@app.route("/invoice")
def invoice():
    search_term = request.args.get("q", "").strip()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if search_term:
        like_term = f"%{search_term}%"
        cursor.execute("""
            SELECT * FROM inventory
            WHERE product_id LIKE %s
               OR name LIKE %s
               OR supplier LIKE %s
               OR category LIKE %s
        """, (like_term, like_term, like_term, like_term))
    else:
        cursor.execute("SELECT * FROM inventory")

    rows = cursor.fetchall()
    conn.close()

    return render_template("invoice.html", rows=rows, search=search_term)

#save invoice
@app.route("/save_invoice", methods=["POST"])
def save_invoice():
    data = request.get_json()

    customer_name = data.get("customer_name", "Walk-in Customer")
    items = data.get("items", [])

    if not items:
        return jsonify({"error": "No items to save"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    # Insert invoice
    cursor.execute("INSERT INTO invoices (customer_name) VALUES (%s)", (customer_name,))
    invoice_id = cursor.lastrowid

    # Insert items
    for item in items:
        cursor.execute("""
            INSERT INTO invoice_items (invoice_id, product_id, quantity, price, subtotal)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            invoice_id,
            item["id"], 
            item["qty"], 
            item["price"], 
            item["qty"] * item["price"]
        ))

    conn.commit()
    conn.close()

    return jsonify({"message": "Invoice saved successfully", "invoice_id": invoice_id})


# List all invoices
@app.route("/invoices")
def invoices():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT i.id, i.customer_name, i.created_at, 
               SUM(ii.subtotal) AS total
        FROM invoices i
        LEFT JOIN invoice_items ii ON i.id = ii.invoice_id
        GROUP BY i.id, i.customer_name, i.created_at
        ORDER BY i.created_at DESC
    """)
    invoices = cursor.fetchall()

    conn.close()
    return render_template("invoices.html", invoices=invoices)

@app.route("/invoice/<int:invoice_id>")
def invoice_detail(invoice_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Invoice header
    cursor.execute("SELECT * FROM invoices WHERE id=%s", (invoice_id,))
    invoice = cursor.fetchone()

    # Invoice items
    cursor.execute("""
        SELECT ii.*, inv.name, inv.image_url
        FROM invoice_items ii
        JOIN inventory inv ON ii.product_id = inv.id
        WHERE ii.invoice_id = %s
    """, (invoice_id,))
    items = cursor.fetchall()

    conn.close()
    return render_template("invoice_detail.html", invoice=invoice, items=items)

@app.route("/invoice/<int:invoice_id>/pdf")
def invoice_pdf(invoice_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch invoice
    cursor.execute("SELECT * FROM invoices WHERE id=%s", (invoice_id,))
    invoice = cursor.fetchone()

    # Fetch items
    cursor.execute("""
        SELECT ii.*, inv.name, inv.image_url 
        FROM invoice_items ii
        JOIN inventory inv ON ii.product_id = inv.id
        WHERE ii.invoice_id=%s
    """, (invoice_id,))
    items = cursor.fetchall()

    conn.close()

    # Create PDF in memory
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = height - 50
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, f"Invoice #{invoice['id']}")
    y -= 30
    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"Customer: {invoice['customer_name']}")
    y -= 20
    p.drawString(50, y, f"Date: {invoice['created_at']}")
    y -= 40

    # Table headers
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Product")
    p.drawString(250, y, "Qty")
    p.drawString(300, y, "Price")
    p.drawString(400, y, "Subtotal")
    y -= 20
    p.line(50, y, 550, y)
    y -= 20

    # Items
    p.setFont("Helvetica", 12)
    total = 0
    for item in items:
        p.drawString(50, y, item["name"])
        p.drawString(250, y, str(item["quantity"]))
        p.drawString(300, y, f"${item['price']:.2f}")
        p.drawString(400, y, f"${item['subtotal']:.2f}")
        total += float(item["subtotal"])
        y -= 20
        if y < 100:
            p.showPage()
            y = height - 50

    # Total
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(300, y, "TOTAL:")
    p.drawString(400, y, f"${total:.2f}")

    p.showPage()
    p.save()

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"invoice_{invoice['id']}.pdf",
        mimetype="application/pdf"
    )

# Edit Invoice
@app.route("/invoice/<int:invoice_id>/edit", methods=["GET", "POST"])
def invoice_edit(invoice_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        # Update customer name
        customer_name = request.form.get("customer_name")
        cursor.execute("UPDATE invoices SET customer_name=%s WHERE id=%s", (customer_name, invoice_id))

        # Update items (loop through form data)
        item_ids = request.form.getlist("item_id")
        quantities = request.form.getlist("quantity")
        prices = request.form.getlist("price")

        for i in range(len(item_ids)):
            cursor.execute("""
                UPDATE invoice_items 
                SET quantity=%s, price=%s, subtotal=%s
                WHERE id=%s
            """, (
                int(quantities[i]),
                float(prices[i]),
                int(quantities[i]) * float(prices[i]),
                int(item_ids[i])
            ))

        conn.commit()
        conn.close()
        return redirect(url_for("invoice_detail", invoice_id=invoice_id))

    # GET → load invoice
    cursor.execute("SELECT * FROM invoices WHERE id=%s", (invoice_id,))
    invoice = cursor.fetchone()

    cursor.execute("""
        SELECT ii.*, inv.name, inv.image_url 
        FROM invoice_items ii
        JOIN inventory inv ON ii.product_id = inv.id
        WHERE ii.invoice_id=%s
    """, (invoice_id,))
    items = cursor.fetchall()

    conn.close()
    return render_template("invoice_edit.html", invoice=invoice, items=items)


if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)