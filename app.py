import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import os
import smtplib
from email.message import EmailMessage

# ----------------------------
# Page config
# ----------------------------
st.set_page_config(page_title="DSC Certificate Automation")
st.title("DSC Certificate Automation System")

st.markdown(
    """
    **Workflow**
    1. Upload event-specific certificate template (PNG)
    2. Upload attendance file (CSV / Excel)
    3. Only eligible participants get certificates
    4. System fills **ONLY the name**
    """
)

# ----------------------------
# Upload certificate template
# ----------------------------
template_file = st.file_uploader(
    "Upload Certificate Template (PNG)",
    type=["png"]
)

# ----------------------------
# Upload attendance file
# ----------------------------
attendance_file = st.file_uploader(
    "Upload Attendance File (CSV or Excel)",
    type=["csv", "xlsx"]
)

# ----------------------------
# Configuration
# ----------------------------
FONT_PATH = "GreatVibes-Regular.ttf"   # put font in same folder
NAME_FONT_SIZE = 72

# ⚠️ Adjust ONCE per template
NAME_POSITION = (750, 500)  # (x, y)

# ----------------------------
# Helper functions
# ----------------------------
def normalize_columns(df):
    df.columns = [c.strip().lower().replace(" ", "") for c in df.columns]
    return df


def normalize_attendance(val):
    if pd.isna(val):
        return "A"
    val = str(val).strip().lower()
    if val in ["p", "present", "yes", "y", "attended", "1"]:
        return "P"
    return "A"


def generate_certificate(name, template_path):
    os.makedirs("certificates", exist_ok=True)

    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    font = ImageFont.truetype(FONT_PATH, NAME_FONT_SIZE)

    draw.text(
        NAME_POSITION,
        name,
        fill="black",
        font=font
    )

    output_path = f"certificates/{name.replace(' ', '_')}.pdf"
    img.save(output_path, "PDF")

    return output_path

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  # SSL
SENDER_EMAIL = "Your_Email_Address"
SENDER_PASSWORD = "Your_app_password"

def send_certificate_email(receiver_email, receiver_name, certificate_path):
    msg = EmailMessage()
    msg["From"] = SENDER_EMAIL
    msg["To"] = receiver_email
    msg["Subject"] = "Your Certificate of Participation"

    msg.set_content(
        f"""Hello {receiver_name},

Congratulations! 🎉

Please find attached your certificate for the event.
Thank you for your participation.

Best regards,
Developer Student Club
"""
    )

    with open(certificate_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename=os.path.basename(certificate_path)
        )

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)

# ----------------------------
# Main logic
# ----------------------------
if template_file and attendance_file:

    # Save template locally
    template_path = "current_template.png"
    with open(template_path, "wb") as f:
        f.write(template_file.read())

    # Read attendance file
    if attendance_file.name.endswith(".csv"):
        df = pd.read_csv(attendance_file)
    else:
        df = pd.read_excel(attendance_file)

    df = normalize_columns(df)

    required_cols = ["name", "email", "day1", "day2", "day3"]
    for col in required_cols:
        if col not in df.columns:
            st.error(f"Missing required column: {col}")
            st.stop()

    for day in ["day1", "day2", "day3"]:
        df[day] = df[day].apply(normalize_attendance)

    eligible_df = df[
        (df["day1"] == "P") &
        (df["day2"] == "P") &
        (df["day3"] == "P")
    ]

    st.subheader("Eligible Participants")
    st.write(f"Total eligible: {len(eligible_df)}")
    st.dataframe(eligible_df[["name", "email"]])

if st.button("Generate & Email Certificates"):
    sent = 0
    for _, row in eligible_df.iterrows():
        cert_path = generate_certificate(
            name=row["name"],
            template_path=template_path
        )

        try:
            send_certificate_email(
                receiver_email=row["email"],
                receiver_name=row["name"],
                certificate_path=cert_path
           )
            sent += 1
        except Exception as e:
            st.error(f"Failed for {row['email']}: {e}")

    st.success(f"✅ Certificates generated & emailed to {sent} participants")

