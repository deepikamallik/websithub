from flask import Flask, render_template, request, redirect, session
import mysql.connector
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, date


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

    required_vars = [
        "MYSQLHOST",
        "MYSQLPORT",
        "MYSQLUSER",
        "MYSQLPASSWORD",
        "MYSQLDATABASE"
    ]

    missing = [
        var for var in required_vars
        if not os.environ.get(var)
    ]

    if missing:
        raise Exception(
            "Missing MySQL environment variables: "
            + ", ".join(missing)
        )

    return mysql.connector.connect(
        host=os.environ.get("MYSQLHOST"),
        port=int(os.environ.get("MYSQLPORT")),
        user=os.environ.get("MYSQLUSER"),
        password=os.environ.get("MYSQLPASSWORD"),
        database=os.environ.get("MYSQLDATABASE"),
        connection_timeout=30,
        autocommit=False
    )


# =========================================================
# EMAIL SETTINGS
# =========================================================

MY_EMAIL = os.environ.get("MY_EMAIL")

APP_PASSWORD = os.environ.get(
    "GMAIL_APP_PASSWORD"
)


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

@app.route(
    "/login",
    methods=["GET", "POST"]
)
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

    session.pop(
        "admin_logged_in",
        None
    )

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
            ORDER BY
                created_at DESC,
                id DESC
        """)

        customer_requests = cursor.fetchall()

        # ---------------------------------------------
        # COUNTS
        # ---------------------------------------------

        total_customers = len(customer_requests)

        pending_count = sum(
            1
            for r in customer_requests
            if (r[6] or "Pending") == "Pending"
        )

        contacted_count = sum(
            1
            for r in customer_requests
            if r[6] == "Contacted"
        )

        completed_count = sum(
            1
            for r in customer_requests
            if r[6] == "Completed"
        )

        return render_template(
            "dashboard.html",
            requests=customer_requests,
            total_customers=total_customers,
            pending_count=pending_count,
            contacted_count=contacted_count,
            completed_count=completed_count,
            current_datetime=datetime.now()
        )

    except Exception as e:

        print(
            "DASHBOARD MYSQL ERROR:",
            e
        )

        return """
        <div style="
            font-family:Arial;
            text-align:center;
            padding:80px;
        ">

            <h2>
                Dashboard Error ❌
            </h2>

            <p>
                Please check your Railway MySQL
                connection and Render environment variables.
            </p>

            <p style="color:#777;">
                Error: """ + str(e) + """
            </p>

            <a href="/login">
                Back to Login
            </a>

        </div>
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

        print(
            "CUSTOMER DETAILS ERROR:",
            e
        )

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

        # ---------------------------------------------
        # UPDATE CUSTOMER
        # ---------------------------------------------

        if request.method == "POST":

            name = request.form.get("name")
            email = request.form.get("email")
            phone = request.form.get("phone")
            website_type = request.form.get(
                "website_type"
            )
            message = request.form.get(
                "message"
            )
            notes = request.form.get(
                "notes"
            )

            follow_up_date = request.form.get(
                "follow_up_date"
            )

            follow_up_time = request.form.get(
                "follow_up_time"
            )

            # -----------------------------------------
            # COMBINE DATE + TIME
            # -----------------------------------------

            follow_up_datetime = None

            if (
                follow_up_date
                and follow_up_time
            ):

                try:

                    follow_up_datetime = datetime.strptime(
                        f"{follow_up_date} {follow_up_time}",
                        "%Y-%m-%d %H:%M"
                    )

                except ValueError:

                    follow_up_datetime = None

            # -----------------------------------------
            # UPDATE DATABASE
            # -----------------------------------------

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
                follow_up_datetime,
                customer_id
            ))

            db.commit()

            print(
                f"CUSTOMER UPDATED: "
                f"{customer_id} ✅"
            )

            return redirect(
                "/dashboard"
            )

        # ---------------------------------------------
        # GET CUSTOMER
        # ---------------------------------------------

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

        print(
            "EDIT CUSTOMER ERROR:",
            e
        )

        return """
        <h2 style="
            text-align:center;
            margin-top:100px;
        ">
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

@app.route(
    "/update-status",
    methods=["POST"]
)
def update_status():

    if not session.get("admin_logged_in"):
        return redirect("/login")

    customer_id = request.form.get(
        "customer_id"
    )

    status = request.form.get(
        "status"
    )

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
            f"STATUS UPDATED: "
            f"Customer {customer_id} "
            f"-> {status} ✅"
        )

    except Exception as e:

        print(
            "STATUS UPDATE ERROR:",
            e
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect("/dashboard")


# =========================================================
# DELETE CUSTOMER
# =========================================================

@app.route(
    "/delete-customer",
    methods=["POST"]
)
def delete_customer():

    if not session.get("admin_logged_in"):
        return redirect("/login")

    customer_id = request.form.get(
        "customer_id"
    )

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
            f"CUSTOMER DELETED: "
            f"{customer_id} ✅"
        )

    except Exception as e:

        print(
            "DELETE CUSTOMER ERROR:",
            e
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect("/dashboard")


# =========================================================
# CONTACT / CUSTOMER REQUEST
# =========================================================

@app.route(
    "/contact",
    methods=["GET", "POST"]
)
def contact():

    if request.method == "POST":

        # ---------------------------------------------
        # BASIC INFORMATION
        # ---------------------------------------------

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        website_type = request.form.get(
            "website_type",
            ""
        ).strip()

        message = request.form.get(
            "message",
            ""
        ).strip()

        # ---------------------------------------------
        # CRM INFORMATION
        # ---------------------------------------------

        notes = request.form.get(
            "notes",
            ""
        ).strip()

        follow_up_date = request.form.get(
            "follow_up_date",
            ""
        ).strip()

        follow_up_time = request.form.get(
            "follow_up_time",
            ""
        ).strip()

        # ---------------------------------------------
        # AUTOMATIC VALUES
        # ---------------------------------------------

        status = "Pending"

        created_at = datetime.now()

        follow_up_datetime = None

        if (
            follow_up_date
            and follow_up_time
        ):

            try:

                follow_up_datetime = datetime.strptime(
                    f"{follow_up_date} {follow_up_time}",
                    "%Y-%m-%d %H:%M"
                )

            except ValueError:

                follow_up_datetime = None

        print(
            "\n******** NEW WEBSITE REQUEST ********"
        )

        print("Name:", name)
        print("Email:", email)
        print("Phone:", phone)
        print(
            "Website Type:",
            website_type
        )
        print(
            "Requirements:",
            message
        )
        print(
            "Status:",
            status
        )
        print(
            "Request Date:",
            created_at.strftime(
                "%Y-%m-%d"
            )
        )
        print(
            "Request Time:",
            created_at.strftime(
                "%H:%M:%S"
            )
        )
        print(
            "Follow-up:",
            follow_up_datetime
        )
        print(
            "Notes:",
            notes
        )

        # ---------------------------------------------
        # SAVE TO MYSQL
        # ---------------------------------------------

        db = None
        cursor = None

        mysql_saved = False

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
                    message,
                    status,
                    created_at,
                    notes,
                    follow_up_date
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )

            """, (
                name,
                email,
                phone,
                website_type,
                message,
                status,
                created_at,
                notes,
                follow_up_datetime
            ))

            db.commit()

            mysql_saved = True

            print(
                "MYSQL: "
                "CUSTOMER REQUEST SAVED ✅"
            )

        except Exception as e:

            if db:
                db.rollback()

            print(
                "MYSQL ERROR:",
                e
            )

        finally:

            if cursor:
                cursor.close()

            if db:
                db.close()

        # ---------------------------------------------
        # SEND EMAIL
        # ---------------------------------------------

        try:

            if (
                MY_EMAIL
                and APP_PASSWORD
            ):

                if follow_up_datetime:

                    follow_up_display = (
                        follow_up_datetime.strftime(
                            "%d %b %Y, %I:%M %p"
                        )
                    )

                else:

                    follow_up_display = (
                        "Not scheduled"
                    )

                msg = EmailMessage()

                msg["Subject"] = (
                    f"New Website Request - {name}"
                )

                msg["From"] = MY_EMAIL

                msg["To"] = MY_EMAIL

                msg.set_content(
                    f"""
New WebsiteHub Customer Request

Customer Name:
{name}

Email:
{email}

Phone:
{phone}

Website Type:
{website_type}

Requirements:
{message}

Status:
{status}

Request Date:
{created_at.strftime("%d %b %Y")}

Request Time:
{created_at.strftime("%I:%M %p")}

Follow-up:
{follow_up_display}

Notes:
{notes or "No notes added"}
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

                    smtp.send_message(
                        msg
                    )

                print(
                    "EMAIL SENT SUCCESSFULLY ✅"
                )

            else:

                print(
                    "Gmail environment variables "
                    "are not configured."
                )

        except Exception as e:

            print(
                "EMAIL ERROR:",
                e
            )

        # ---------------------------------------------
        # SUCCESS PAGE
        # ---------------------------------------------

        if mysql_saved:

            return """
            <!DOCTYPE html>

            <html lang="en">

            <head>

                <meta charset="UTF-8">

                <meta
                    name="viewport"
                    content="width=device-width,
                    initial-scale=1.0"
                >

                <title>
                    Request Sent | WebsiteHub
                </title>

                <style>

                    * {
                        box-sizing: border-box;
                    }

                    body {
                        margin: 0;
                        min-height: 100vh;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        font-family: Arial, sans-serif;
                        background:
                            linear-gradient(
                                135deg,
                                #f5eaff,
                                #ffe8f5
                            );
                    }

                    .success-box {
                        width: 90%;
                        max-width: 550px;
                        padding: 45px 30px;
                        text-align: center;
                        background: white;
                        border-radius: 24px;
                        box-shadow:
                            0 20px 60px
                            rgba(100, 60, 140, 0.18);
                    }

                    .icon {
                        font-size: 55px;
                        margin-bottom: 15px;
                    }

                    h1 {
                        color: #7146c1;
                        margin-bottom: 12px;
                    }

                    p {
                        color: #666;
                        line-height: 1.7;
                    }

                    .btn {
                        display: inline-block;
                        margin-top: 20px;
                        padding: 13px 28px;
                        border-radius: 30px;
                        background:
                            linear-gradient(
                                135deg,
                                #9b6cff,
                                #e88bc7
                            );
                        color: white;
                        text-decoration: none;
                        font-weight: bold;
                    }

                </style>

            </head>

            <body>

                <div class="success-box">

                    <div class="icon">
                        🎉
                    </div>

                    <h1>
                        Request Sent Successfully!
                    </h1>

                    <p>
                        Thank you for contacting
                        WebsiteHub.
                    </p>

                    <p>
                        Your request has been saved
                        successfully and our team
                        will contact you soon.
                    </p>

                    <a
                        href="/"
                        class="btn"
                    >
                        Back to Website
                    </a>

                </div>

            </body>

            </html>
            """

        return """
        <h2 style="
            text-align:center;
            margin-top:100px;
        ">
            Request could not be saved ❌
        </h2>

        <p style="
            text-align:center;
            color:#777;
        ">
            Please try again later.
        </p>

        <div style="
            text-align:center;
        ">
            <a href="/contact">
                Return to Contact
            </a>
        </div>
        """

    return render_template(
        "contact.html"
    )


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
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )