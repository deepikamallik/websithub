from flask import Flask, render_template, request, redirect, session
import mysql.connector
import os
import smtplib
from email.message import EmailMessage


app = Flask(__name__)

# =========================================================
# FLASK SECRET KEY
# =========================================================

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "websitehub-local-secret-key"
)


# =========================================================
# MYSQL CONNECTION
# =========================================================

def get_db_connection():
    url = os.environ.get("MYSQL_PUBLIC_URL")
    if url:
        # Parse the URL to extract connection parameters
        import urllib.parse as urlparse
        parsed_url = urlparse.urlparse(url)
        return mysql.connector.connect(
            host=parsed_url.hostname,
            port=parsed_url.port or 20891,
            user=parsed_url.username,
            password=parsed_url.password,
            database=parsed_url.path.lstrip('/')
        )
    return mysql.connector.connect(

        host=os.environ.get("MYSQLHOST"),
        port=int(os.environ.get("MYSQLPORT", "20891")),
        user=os.environ.get("MYSQLUSER"),
        password=os.environ.get("MYSQLPASSWORD"),
        database=os.environ.get("MYSQLDATABASE")
    )


# =========================================================
# EMAIL SETTINGS
# =========================================================

MY_EMAIL = os.environ.get(
    "MY_EMAIL",
    "deepikamallik2006@gmail.com"
)

APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# WEBSITES
# =========================================================

@app.route("/websites")
def websites():
    return render_template("websites.html")


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        admin_username = os.environ.get(
            "ADMIN_USERNAME",
            "admin"
        )

        admin_password = os.environ.get(
            "ADMIN_PASSWORD",
            "admin123"
        )

        if (
            username == admin_username
            and password == admin_password
        ):

            session["admin_logged_in"] = True

            return redirect("/dashboard")

        return render_template(
            "login.html",
            error="Invalid username or password ❌"
        )

    return render_template("login.html")


# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.pop("admin_logged_in", None)

    return redirect("/login")


# =========================================================
# CRM DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if not session.get("admin_logged_in"):
        return redirect("/login")

    db = None
    cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            SELECT
                id,
                name,
                email,
                phone,
                website_type,
                message,
                status,
                created_at,
                notes,
                follow_up_date
            FROM customer_requests
            ORDER BY created_at DESC
        """)

        customer_requests = cursor.fetchall()

        return render_template(
            "dashboard.html",
            requests=customer_requests
        )

    except Exception as e:

        print("DASHBOARD MYSQL ERROR:", e)

        return """
        <h2 style="text-align:center;margin-top:100px;">
            Dashboard Error ❌
        </h2>

        <p style="text-align:center;">
            Please check the database connection.
        </p>
        """

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# VIEW CUSTOMER DETAILS
# =========================================================

@app.route("/customer/<int:customer_id>")
def customer_details(customer_id):

    if not session.get("admin_logged_in"):
        return redirect("/login")

    db = None
    cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            SELECT
                id,
                name,
                email,
                phone,
                website_type,
                message,
                status,
                created_at,
                notes,
                follow_up_date
            FROM customer_requests
            WHERE id = %s
        """, (customer_id,))

        customer = cursor.fetchone()

        if customer is None:
            return "Customer not found", 404

        return render_template(
            "customer_details.html",
            customer=customer
        )

    except Exception as e:

        print("CUSTOMER DETAILS ERROR:", e)

        return """
        <h2 style="text-align:center;margin-top:100px;">
            Customer Details Error ❌
        </h2>
        """

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# EDIT CUSTOMER
# =========================================================

@app.route(
    "/edit-customer/<int:customer_id>",
    methods=["GET", "POST"]
)
def edit_customer(customer_id):

    if not session.get("admin_logged_in"):
        return redirect("/login")

    db = None
    cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor()

        # -------------------------------------------------
        # SAVE CUSTOMER
        # -------------------------------------------------

        if request.method == "POST":

            name = request.form.get("name")
            email = request.form.get("email")
            phone = request.form.get("phone")
            website_type = request.form.get("website_type")
            message = request.form.get("message")
            notes = request.form.get("notes")
            follow_up_date = request.form.get("follow_up_date")

            if not follow_up_date:
                follow_up_date = None

            cursor.execute("""
                UPDATE customer_requests
                SET
                    name = %s,
                    email = %s,
                    phone = %s,
                    website_type = %s,
                    message = %s,
                    notes = %s,
                    follow_up_date = %s
                WHERE id = %s
            """, (
                name,
                email,
                phone,
                website_type,
                message,
                notes,
                follow_up_date,
                customer_id
            ))

            db.commit()

            print(
                f"CUSTOMER UPDATED: {customer_id} ✅"
            )

            return redirect("/dashboard")

        # -------------------------------------------------
        # GET CUSTOMER
        # -------------------------------------------------

        cursor.execute("""
            SELECT
                id,
                name,
                email,
                phone,
                website_type,
                message,
                status,
                created_at,
                notes,
                follow_up_date
            FROM customer_requests
            WHERE id = %s
        """, (customer_id,))

        customer = cursor.fetchone()

        if customer is None:
            return "Customer not found", 404

        return render_template(
            "edit_customer.html",
            customer=customer
        )

    except Exception as e:

        print("EDIT CUSTOMER ERROR:", e)

        return """
        <h2 style="text-align:center;margin-top:100px;">
            Edit Customer Error ❌
        </h2>
        """

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# UPDATE CUSTOMER STATUS
# =========================================================

@app.route("/update-status", methods=["POST"])
def update_status():

    if not session.get("admin_logged_in"):
        return redirect("/login")

    customer_id = request.form.get("customer_id")
    status = request.form.get("status")

    allowed_statuses = [
        "Pending",
        "Contacted",
        "Completed"
    ]

    if status not in allowed_statuses:
        return redirect("/dashboard")

    db = None
    cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            UPDATE customer_requests
            SET status = %s
            WHERE id = %s
        """, (
            status,
            customer_id
        ))

        db.commit()

        print(
            f"STATUS UPDATED: Customer {customer_id} -> {status} ✅"
        )

    except Exception as e:

        print("STATUS UPDATE ERROR:", e)

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect("/dashboard")


# =========================================================
# DELETE CUSTOMER
# =========================================================

@app.route("/delete-customer", methods=["POST"])
def delete_customer():

    if not session.get("admin_logged_in"):
        return redirect("/login")

    customer_id = request.form.get("customer_id")

    db = None
    cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            DELETE FROM customer_requests
            WHERE id = %s
        """, (customer_id,))

        db.commit()

        print(
            f"CUSTOMER DELETED: {customer_id} ✅"
        )

    except Exception as e:

        print("DELETE CUSTOMER ERROR:", e)

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect("/dashboard")


# =========================================================
# CONTACT
# =========================================================

@app.route("/contact", methods=["GET", "POST"])
def contact():

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        website_type = request.form.get("website_type")
        message = request.form.get("message")

        print("\n******** NEW WEBSITE REQUEST ********")
        print("Name:", name)
        print("Email:", email)
        print("Phone:", phone)
        print("Website Type:", website_type)
        print("Requirements:", message)

        # -------------------------------------------------
        # SAVE TO MYSQL
        # -------------------------------------------------

        db = None
        cursor = None

        try:

            db = get_db_connection()
            cursor = db.cursor()

            cursor.execute("""
                INSERT INTO customer_requests
                (
                    name,
                    email,
                    phone,
                    website_type,
                    message
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                name,
                email,
                phone,
                website_type,
                message
            ))

            db.commit()

            print("MYSQL: CUSTOMER REQUEST SAVED ✅")

        except Exception as e:

            print("MYSQL ERROR:", e)

        finally:

            if cursor:
                cursor.close()

            if db:
                db.close()

        # -------------------------------------------------
        # SEND EMAIL
        # -------------------------------------------------

        try:

            if APP_PASSWORD:

                msg = EmailMessage()

                msg["Subject"] = (
                    f"New Website Request - {name}"
                )

                msg["From"] = MY_EMAIL
                msg["To"] = MY_EMAIL

                msg.set_content(
                    f"""
New Website Request

Name: {name}
Email: {email}
Phone: {phone}
Website Type: {website_type}

Requirements:
{message}
"""
                )

                with smtplib.SMTP_SSL(
                    "smtp.gmail.com",
                    465
                ) as smtp:

                    smtp.login(
                        MY_EMAIL,
                        APP_PASSWORD
                    )

                    smtp.send_message(msg)

                print("EMAIL SENT SUCCESSFULLY ✅")

            else:

                print(
                    "GMAIL_APP_PASSWORD is not set."
                )

        except Exception as e:

            print("EMAIL ERROR:", e)

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        return """
        <!DOCTYPE html>

        <html>

        <head>
            <title>Request Sent</title>
        </head>

        <body style="
            font-family:Arial;
            text-align:center;
            padding-top:100px;
            background:#f5f3ff;
        ">

            <h1 style="color:#4f46e5;">
                Request Sent Successfully! 🎉
            </h1>

            <p>
                Thank you for contacting WebsiteHub.
            </p>

            <p>
                Your request has been received.
            </p>

            <br>

            <a
                href="/"
                style="
                    text-decoration:none;
                    background:#4f46e5;
                    color:white;
                    padding:12px 25px;
                    border-radius:8px;
                "
            >
                Back to Website
            </a>

        </body>

        </html>
        """

    return render_template("contact.html")


# =========================================================
# DEMO WEBSITES
# =========================================================

@app.route("/demo/restaurant")
def restaurant_demo():
    return render_template(
        "demos/restaurant.html"
    )


@app.route("/demo/business")
def business_demo():
    return render_template(
        "demos/business.html"
    )


@app.route("/demo/portfolio")
def portfolio_demo():
    return render_template(
        "demos/portfolio.html"
    )


@app.route("/demo/ecommerce")
def ecommerce_demo():
    return render_template(
        "demos/ecommerce.html"
    )


# =========================================================
# RUN FLASK
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )