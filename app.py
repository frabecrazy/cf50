import streamlit as st
import pandas as pd
import random
import plotly.express as px
import time

st.set_page_config(page_title="Digital Carbon Footprint Calculator", layout="wide")

# Init session state
if "page" not in st.session_state or st.session_state.page not in ["intro", "main", "results"]:
    st.session_state.page = "intro"
if "role" not in st.session_state:
    st.session_state.role = ""
if "device_inputs" not in st.session_state:
    st.session_state.device_inputs = {}
if "results" not in st.session_state:
    st.session_state.results = {}
activity_factors = {
    "Student": {
        "MS Office (e.g. Excel, Word, PPT…)": 0.00901,
        "Technical softwares (e.g. Matlab, Python…)": 0.00901,
        "Web browsing": 0.0264,
        "Watching lecture recordings": 0.0439,
        "Online classes streaming or video call": 0.112,
        "Reading study materials on your computer (e.g. slides, articles, digital textbooks)": 0.00901
    },
    "Professor": {
        "MS Office (e.g. Excel, Word, PPT…)": 0.00901,
        "Web browsing": 0.0264,
        "Videocall (e.g. Zoom, Teams…)": 0.112,
        "Online classes streaming": 0.112,
        "Reading materials on your computer (e.g. slides, articles, digital textbooks)": 0.00901,
        "Technical softwares (e.g. Matlab, Python…)": 0.00901
    },
    "Staff Member": {
        "MS Office (e.g. Excel, Word, PPT…)": 0.00901,
        "Management software (e.g. SAP)": 0.00901,
        "Web browsing": 0.0264,
        "Videocall (e.g. Zoom, Teams…)": 0.112,
        "Reading materials on your computer (e.g. documents)": 0.00901
    }
}

ai_factors = {
    "Summarize texts or articles": 0.000711936,
    "Translate sentences or texts": 0.000363008,
    "Explain a concept": 0.000310784,
    "Generate quizzes or questions": 0.000539136,
    "Write formal emails or messages": 0.000107776,
    "Correct grammar or style": 0.000107776,
    "Analyze long PDF documents": 0.001412608,
    "Write or test code": 0.002337024,
    "Generate images": 0.00206,
    "Brainstorm for thesis or projects": 0.000310784,
    "Explain code step-by-step": 0.003542528,
    "Prepare lessons or presentations": 0.000539136
}

device_ef = {
    "Desktop Computer": 296,
    "Laptop Computer": 170,
    "Smartphone": 38.4,
    "Tablet": 87.1,
    "External Monitor": 235,
    "Headphones": 12.17,
    "Printer": 62.3,
    "Router/Modem": 106
}

eol_modifier = {
    "I bring it to a certified e-waste collection center": -0.224,
    "I throw it away in general waste": 0.611,
    "I return it to manufacturer for recycling or reuse": -0.3665,
    "I sell or donate it to someone else": -0.445,
    "I store it at home, unused": 0.402
}

DAYS = 250  # Typical number of work/study days per year

def show_main():
    # --- STILE GLOBALE ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        h1, h2, h3, h4 {
            color: #1d3557;
        }

        .device-box {
            background-color: #f1faee;
            border-left: 6px solid #52b788;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }

        .device-label {
            font-weight: 600;
            font-size: 0.95em;
            margin-bottom: 4px;
            color: #1d3557;
        }

        .device-hint {
            font-size: 12px;
            color: gray;
        }

        .impact-text {
            font-size: 1em;
            color: #1b4332;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- TITOLO ---
    st.markdown("""
        <div style="background: linear-gradient(to right, #d8f3dc, #a8dadc);
                    padding: 30px 20px;
                    border-radius: 15px;
                    text-align: center;
                    box-shadow: 0 4px 18px rgba(0,0,0,0.06);
                    margin-bottom: 30px;">
            <h1 style="font-size: 2.4em;">☁️ Digital Usage Form</h1>
        </div>
    """, unsafe_allow_html=True)

    # === DEVICES ===
    st.header("💻 Devices")
    st.markdown("""
Choose the digital devices you currently use, and for each one, provide a few details about how you use it and what you do when it's no longer needed.
""")

    if "device_list" not in st.session_state:
        st.session_state.device_list = []

    device_to_add = st.selectbox("Select a device and click 'Add Device', repeat for all the devices you own", list(device_ef.keys()))
    if st.button("➕ Add Device"):
        count = sum(d.startswith(device_to_add) for d in st.session_state.device_list)
        new_id = f"{device_to_add}_{count}"
        st.session_state.device_list.append(new_id)
        st.session_state.device_inputs[new_id] = {
            "years": 1.0,
            "used": "New",
            "shared": "Personal",
            "eol": "I bring it to a certified e-waste collection center"
        }
        st.success(f"{device_to_add} added successfully!")

    total_prod, total_eol = 0, 0

    for device_id in st.session_state.device_list:
        base_device = device_id.rsplit("_", 1)[0]
        st.subheader(base_device)

        prev = st.session_state.device_inputs[device_id]
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("**Device's lifespan**<br/><span class='device-hint'>How many years you plan to use the device in total</span>", unsafe_allow_html=True)
            years = st.number_input("", 0.5, 20.0, step=0.5, format="%.1f", key=f"{device_id}_years")

        with col2:
            st.markdown("**Condition**<br/><span class='device-hint'>Was the device new or used when you got it?</span>", unsafe_allow_html=True)
            used = st.selectbox("", ["New", "Used"], index=["New", "Used"].index(prev["used"]), key=f"{device_id}_used")

        with col3:
            st.markdown("**Ownership**<br/><span class='device-hint'>Is this device used only by you or shared?</span>", unsafe_allow_html=True)
            shared = st.selectbox("", ["Personal", "Shared"], index=["Personal", "Shared"].index(prev["shared"]), key=f"{device_id}_shared")

        with col4:
            st.markdown("**End-of-life behavior**<br/><span class='device-hint'>What do you usually do when the device reaches its end of life?</span>", unsafe_allow_html=True)
            eol = st.selectbox("", list(eol_modifier.keys()), index=list(eol_modifier.keys()).index(prev["eol"]), key=f"{device_id}_eol")

        st.session_state.device_inputs[device_id] = {
            "years": years,
            "used": used,
            "shared": shared,
            "eol": eol
        }

        if st.button(f"🗑 Remove {base_device}", key=f"remove_{device_id}"):
            st.session_state.device_list.remove(device_id)
            st.session_state.device_inputs.pop(device_id, None)
            st.rerun()

        impact = device_ef[base_device]
        if used == "New" and shared == "Personal":
            adj_years = years
        elif used == "Used" and shared == "Personal":
            adj_years = years + (years / 2)
        elif used == "New" and shared == "Shared":
            adj_years = years * 3
        else:
            adj_years = years * 4.5

        eol_mod = eol_modifier[eol]
        prod_per_year = impact / adj_years
        eol_impact = (impact * eol_mod) / adj_years

        total_prod += prod_per_year
        total_eol += eol_impact

        st.markdown(f"<div class='impact-text'>📊 <strong>Production</strong>: {prod_per_year:.2f} kg CO₂e/year &nbsp;&nbsp;&nbsp; <strong>End-of-life</strong>: {eol_impact:.2f} kg CO₂e/year</div>", unsafe_allow_html=True)


    # === DIGITAL ACTIVITIES ===
    st.markdown("""
        <style>
        .section-header {
            color: #1d3557;
            font-size: 1.8em;
            margin-top: 40px;
        }

        .activity-desc {
            font-size: 18px;
            color: #333;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='section-header'>🎓 Digital Activities</div>", unsafe_allow_html=True)
    st.markdown("""
<span class='activity-desc'>
Estimate how many hours per day you spend on each activity during a typical 8-hour study or work day.  
You may exceed 8 hours if multitasking (e.g., watching a lecture while writing notes).
</span>
""", unsafe_allow_html=True)

    role = st.session_state.role
    ore_dict = {}
    digital_total = 0

    col1, col2 = st.columns(2)

    for i, (act, ef) in enumerate(activity_factors[role].items()):
        with (col1 if i % 2 == 0 else col2):
            ore = st.slider(f"{act} (h/day)", min_value=0.0, max_value=8.0, value=0.0, step=0.5, key=act)
            ore_dict[act] = ore
            digital_total += ore * ef * DAYS

    st.markdown("<br><br>", unsafe_allow_html=True)

    st.markdown("""
<span class='activity-desc'>
Now tell us more about your habits related to email, cloud, printing and connectivity.
</span>
""", unsafe_allow_html=True)

    email_plain = st.selectbox(
        "Emails sent/received during a typical 8-hour day **no attachments** - do not include spam emails",
        ["1–10", "11–20", "21–30", "31–40", "> 40"]
    )

    email_attach = st.selectbox(
        "Emails sent/received during a typical 8-hour day **with attachments** - do not include spam emails",
        ["1–10", "11–20", "21–30", "31–40", "> 40"]
    )

    emails = {"1–10": 5, "11–20": 15, "21–30": 25, "31–40": 35, "> 40": 45}

    cloud = st.selectbox(
        "Cloud storage you currently use **for academic or work-related files** (e.g., on iCloud, Google Drive, OneDrive)",
        ["<5GB", "5–20GB", "20–50GB", "50–100GB"]
    )

    cloud_gb = {"<5GB": 3, "5–20GB": 13, "20–50GB": 35, "50–100GB": 75}

    wifi = st.slider(
        "Estimate your daily Wi-Fi connection time during a typical 8-hour study or work day, including hours when you're not actively using your device (e.g., background apps, idle mode)",
        0.0, 8.0, 4.0, 0.5
    )

    pages = st.number_input(
        "Number of pages you print per day for academic or work purposes",
        0, 100, 0
    )

    idle = st.radio(
        "When you're not using your computer...",
        ["I turn it off", "I leave it on (idle mode)", "I don’t have a computer"]
    )

    mail_total = emails[email_plain] * 0.004 * DAYS + emails[email_attach] * 0.035 * DAYS + cloud_gb[cloud] * 0.01
    wifi_total = wifi * 0.00584 * DAYS
    print_total = pages * 0.0045 * DAYS

    if idle == "I leave it on (idle mode)":
        idle_total = DAYS * 0.0104 * 16
    elif idle == "I turn it off":
        idle_total = DAYS * 0.0005204 * 16
    else:  # "I don’t have a computer"
        idle_total = 0

    digital_total += mail_total + wifi_total + print_total + idle_total



    # === AI TOOLS ===
    st.markdown("""
        <style>
        .section-header {
            color: #1d3557;
            font-size: 1.8em;
            margin-top: 40px;
        }

        .ai-desc {
            font-size: 17px;
            color: #333;
            margin-bottom: 15px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='section-header'>🤖 AI Tools</div>", unsafe_allow_html=True)
    st.markdown("<div class='ai-desc'>Estimate how many queries you make per day for each AI-powered task.</div>", unsafe_allow_html=True)

    ai_total = 0
    cols = st.columns(2)

    for i, (task, ef) in enumerate(ai_factors.items()):
        with cols[i % 2]:
            q = st.number_input(f"{task} (queries/day)", 0, 100, 0, key=task)
            ai_total += q * ef * DAYS


    # === FINAL BUTTON ===
    st.markdown("""
        <style>
        .final-button {
            margin-top: 50px;
            text-align: center;
        }

        .final-button button {
            background-color: #52b788 !important;
            color: white !important;
            font-size: 1.1em !important;
            padding: 0.6em 1.2em !important;
            border-radius: 8px !important;
            border: none !important;
        }

        .final-button button:hover {
            background-color: #40916c !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="final-button">', unsafe_allow_html=True)
    if st.button("🌍 Discover Your Digital Carbon Footprint!"):
        st.session_state.results = {
            "Devices": total_prod,
            "E-Waste": total_eol,
            "Digital Activities": digital_total,
            "AI Tools": ai_total
        }
        st.session_state.page = "results"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)



def show_intro():
    # --- STILE GLOBALE ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        h1, h2, h3, h4 {
            color: #1d3557;
        }

        .intro-box {
            background: linear-gradient(to right, #d8f3dc, #a8dadc);
            padding: 40px 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 18px rgba(0,0,0,0.06);
            margin-bottom: 30px;
        }

        .selectbox-container {
            background-color: #f1faee;
            border-left: 5px solid #52b788;
            border-radius: 10px;
            padding: 20px;
            margin-top: 25px;
        }

        .start-button {
            margin-top: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- HERO INTUITIVO ---
    st.markdown("""
        <div class="intro-box">
            <h1 style="font-size: 2.6em;">📱 Digital Carbon Footprint Calculator</h1>
        </div>
    """, unsafe_allow_html=True)

    # --- TESTO DESCRITTIVO ---
    st.markdown("""
Welcome to the **Digital Carbon Footprint Calculator**, a tool developed within the *Green DiLT* project to raise awareness about the hidden environmental impact of digital habits in academia.

This calculator is tailored for **university students, professors, and staff members**, helping you estimate your CO₂e emissions from everyday digital activities — often overlooked, but increasingly relevant.

---

👉 Select your role to begin:
""")

    # --- SELECTBOX ---
    with st.container():
        st.session_state.role = st.selectbox(
            "What is your role in academia?",
            ["", "Student", "Professor", "Staff Member"]
        )

    # --- BOTTONE START ---
    st.markdown('<div class="start-button">', unsafe_allow_html=True)
    if st.button("➡️ Start Calculation"):
        if st.session_state.role:
            st.session_state.page = "main"
            st.rerun()
        else:
            st.warning("Please select your role before continuing.")
    st.markdown('</div>', unsafe_allow_html=True)



def show_results():

    # --- STILE GLOBALE ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        h1, h2, h3, h4 {
            color: #1d3557;
        }

        .tip-card {
            background-color: #e3fced;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
        }

        .equiv-card {
            background-color: white;
            border-left: 6px solid #52b788;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            text-align: center;
        }

        .equiv-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
        }

        footer {
            text-align: center;
            font-size: 0.8em;
            color: #999;
            margin-top: 40px;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- HERO SECTION ---
    st.markdown("""
        <div style="
            background: linear-gradient(to right, #d8f3dc, #a8dadc);
            padding: 40px 20px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            margin-bottom: 30px;
        ">
            <h1 style="font-size: 2.8em; margin-bottom: 0.1em;">🌍 Your Digital Carbon Footprint</h1>
            <p style="font-size: 1.2em; color: #1b4332;">Discover your impact — and what to do about it.</p>
        </div>
    """, unsafe_allow_html=True)

    res = st.session_state.results
    total = sum(res.values())

    # --- CARICAMENTO ---
    with st.spinner("🔍 Calculating your footprint..."):
        time.sleep(1.2)

    # --- RISULTATO TOTALE ---
    st.markdown(f"""
        <div style="background-color:#d8f3dc; border-left: 6px solid #1b4332;
                    padding: 1em 1.5em; margin-top: 20px; border-radius: 10px;">
            <h3 style="margin: 0; font-size: 1.6em;">🌱 Total CO₂e:</h3>
            <p style="font-size: 2.2em; font-weight: bold; color: #1b4332; margin: 0;">
                {total:.0f} kg/year
            </p>
        </div>
    """, unsafe_allow_html=True)

    # --- METRICHE IN GRIGLIA ---
    st.markdown("<br><h4>📦 Breakdown by source:</h4>", unsafe_allow_html=True)
    st.markdown(f"""
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px;">
            <div class="tip-card" style="text-align:center;">
                <div style="font-size: 2em;">💻</div>
                <div style="font-size: 1.2em;"><b>{res['Devices']:.2f} kg</b></div>
                <div style="color: #555;">Devices</div>
            </div>
            <div class="tip-card" style="text-align:center;">
                <div style="font-size: 2em;">🗑️</div>
                <div style="font-size: 1.2em;"><b>{res['E-Waste']:.2f} kg</b></div>
                <div style="color: #555;">E-Waste</div>
            </div>
            <div class="tip-card" style="text-align:center;">
                <div style="font-size: 2em;">📡</div>
                <div style="font-size: 1.2em;"><b>{res['Digital Activities']:.2f} kg</b></div>
                <div style="color: #555;">Digital Activities</div>
            </div>
            <div class="tip-card" style="text-align:center;">
                <div style="font-size: 2em;">🤖</div>
                <div style="font-size: 1.2em;"><b>{res['AI Tools']:.2f} kg</b></div>
                <div style="color: #555;">AI Tools</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # --- GRAFICO ---
    st.subheader("📊 Breakdown by Category")
    df_plot = pd.DataFrame({
        "Category": ["Devices", "Digital Activities", "Artificial Intelligence", "E-Waste"],
        "CO₂e (kg)": [res["Devices"], res["Digital Activities"], res["AI Tools"], res["E-Waste"]]
    })

    fig = px.bar(df_plot,
                 x="CO₂e (kg)",
                 y="Category",
                 orientation="h",
                 color="Category",
                 color_discrete_sequence=["#95d5b2", "#74c69d", "#52b788", "#1b4332"],
                 height=400)

    fig.update_layout(showlegend=False, 
                      plot_bgcolor="#f1faee", 
                      paper_bgcolor="#f1faee",
                      font_family="Inter")

    fig.update_traces(marker=dict(line=dict(width=1.5, color='white')))
    st.plotly_chart(fig, use_container_width=True)


    # --- TIPS PERSONALIZZATI ---
    detailed_tips = {
        "Devices": [
            "<b>Turn off devices when not in use</b> – Even in standby mode, they consume energy. Powering them off saves electricity and extends their lifespan.",
            "<b>Update software regularly</b> – This enhances efficiency and performance, often reducing energy consumption.",
            "<b>Activate power-saving settings, reduce screen brightness and enable dark mode</b> – This lower energy use.",
            "<b>Choose accessories made from recycled or sustainable materials</b> – This minimizes the environmental impact of your tech choices."
        ],
        "E-Waste": [
            "<b>Avoid upgrading devices every year</b> – Extending device lifespan significantly reduces environmental impact.",
            "<b>Repair instead of replacing</b> – Fix broken electronics whenever possible to avoid unnecessary waste.",
            "<b>Consider buying refurbished devices</b> – They’re often as good as new, but with a much lower environmental footprint.",
            "<b>Recycle unused electronics properly</b> – Don’t store old devices at home or dispose of them in the environment! E-waste contains polluting and valuable materials that need specialized treatment."
        ],
        "Digital Activities": [
            "<b>Use your internet mindfully</b> – Close unused apps, avoid sending large attachments, and turn off video during calls when not essential.",
            "<b>Declutter your digital space</b> – Regularly delete unnecessary files, empty trash and spam folders, and clean up cloud storage to reduce digital pollution.",
            "<b>Share links instead of attachments</b> – For example, link to a document on OneDrive or Google Drive instead of attaching it in an email.",
            "<b>Use instant messaging for short, urgent messages</b> – It's more efficient than email for quick communications."
        ],
        "Artificial Intelligence": [
            "<b>Use search engines for simple tasks</b> – They consume far less energy than AI tools.",
            "<b>Disable AI-generated results in search engines</b> – (e.g., on Bing: go to Settings > Search > Uncheck \"Include AI-powered answers\" or similar option)",
            "<b>Prefer smaller AI models when possible</b> – For basic tasks, use lighter versions like GPT-4o-mini instead of more energy-intensive models.",
            "<b>Be concise in AI prompts and require concise answers</b> – Short inputs and outputs require less processing."
        ]
    }

    # --- TITOLO + TIPS PER LA CATEGORIA PRINCIPALE ---
    most_impact_cat = df_plot.sort_values("CO₂e (kg)", ascending=False).iloc[0]["Category"]

    st.markdown(f"### 💡 Your biggest impact comes from: <b>{most_impact_cat}</b>", unsafe_allow_html=True)

    with st.expander("📌 Tips to reduce your footprint"):
        for tip in detailed_tips[most_impact_cat]:
            st.markdown(f"""
                <div style="background-color: #e3fced; padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                    {tip}
                </div>
            """, unsafe_allow_html=True)

    # --- EXTRA TIPS ---
    other_categories = [cat for cat in detailed_tips if cat != most_impact_cat]
    extra_tips = [random.choice(detailed_tips[cat]) for cat in random.sample(other_categories, 3)]

    st.markdown("### 💡 Some Extra Tips:")

    with st.expander("📌 Bonus advice from other categories"):
        for tip in extra_tips:
            st.markdown(f"""
                <div style="background-color: #e3fced; padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                    {tip}
                </div>
            """, unsafe_allow_html=True)



    st.divider()

    # --- EQUIVALENZE VISUALI ---
    st.markdown("### ♻️ With the same emissions, you could…")

    burger_eq = total / 4.6
    led_days_eq = (total / 0.256) / 24
    car_km_eq = total / 0.17
    netflix_hours_eq = total / 0.055

    st.markdown(f"""
        <style>
        .equiv-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 25px;
            margin-top: 25px;
        }}
        .equiv-card {{
            background-color: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            border-left: 6px solid #52b788;
            text-align: center;
            transition: transform 0.2s ease;
        }}
        .equiv-card:hover {{
            transform: scale(1.02);
        }}
        .equiv-emoji {{
            font-size: 3.5em;
            margin-bottom: 15px;
        }}
        .equiv-text {{
            font-size: 1.05em;
            line-height: 1.6;
            color: #333;
        }}
        .equiv-value {{
            font-weight: 600;
            font-size: 1.2em;
            color: #1b4332;
        }}
        </style>

        <div class="equiv-grid">
            <div class="equiv-card">
                <div class="equiv-emoji">🍔</div>
                <div class="equiv-text">
                    Produce <span class="equiv-value">~{burger_eq:.0f}</span> beef burgers
                </div>
            </div>
            <div class="equiv-card">
                <div class="equiv-emoji">💡</div>
                <div class="equiv-text">
                    Keep 100 LED bulbs (10W) on for <span class="equiv-value">~{led_days_eq:.0f}</span> days
                </div>
            </div>
            <div class="equiv-card">
                <div class="equiv-emoji">🚗</div>
                <div class="equiv-text">
                    Drive a gasoline car for <span class="equiv-value">~{car_km_eq:.0f}</span> km
                </div>
            </div>
            <div class="equiv-card">
                <div class="equiv-emoji">📺</div>
                <div class="equiv-text">
                    Watch Netflix for <span class="equiv-value">~{netflix_hours_eq:.0f}</span> hours
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- FINALE MOTIVAZIONALE ---

    st.markdown("""
        <div style="text-align: center; padding: 40px 10px;">
            <h2 style="color: #1d3557;">🌱 You did it!</h2>
            <p style="font-size: 1.1em;">Just by completing this tool, you're already part of the solution.<br>
            Digital emissions are invisible, but not insignificant.</p>
        </div>
    """, unsafe_allow_html=True)

    # --- PULSANTE RESTART ---
    st.markdown("### ")
    if st.button("🔁 Restart the Calculator"):
        st.session_state.clear()
        st.session_state.page = "intro"
        st.rerun()




# === PAGE NAVIGATION ===
if st.session_state.page == "intro":
    show_intro()
elif st.session_state.page == "main":
    show_main()
elif st.session_state.page == "results":
    show_results()
