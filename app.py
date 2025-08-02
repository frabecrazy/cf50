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
    st.title("☁️ Digital Usage Form")

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
        prev = st.session_state.device_inputs[device_id]

        # --- CARD ESTETICA ---
        st.markdown(f"""
            <div style="
                background-color: #f8fdfc;
                border-left: 6px solid #52b788;
                padding: 25px 25px 15px 25px;
                border-radius: 12px;
                margin-bottom: 30px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.06);
                position: relative;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <h4 style="margin: 0; color: #1d3557;">{base_device}</h4>
        """, unsafe_allow_html=True)

        # --- BOTTONE REMOVE (lasciato così com'è) ---
        st.form("remove_form_" + device_id)
        st.markdown("""
                    <form action="" method="post">
                        <button type="submit" name="remove" style="
                            background-color: #e63946;
                            border: none;
                            color: white;
                            padding: 6px 12px;
                            border-radius: 6px;
                            font-size: 0.9em;
                            cursor: pointer;
                        ">🗑 Remove</button>
                    </form>
                </div>
        """, unsafe_allow_html=True)

        # --- INPUTS ---
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("**⏳ Device's lifespan**<br/><span style='font-size:12px; color:gray'>How many years you plan to use the device in total</span>", unsafe_allow_html=True)
            years = st.number_input("", 0.5, 20.0, step=0.5, format="%.1f", key=f"{device_id}_years")

        with col2:
            st.markdown("**🔧 Condition**<br/><span style='font-size:12px; color:gray'>Was the device new or used when you got it?</span>", unsafe_allow_html=True)
            used = st.selectbox("", ["New", "Used"], index=["New", "Used"].index(prev["used"]), key=f"{device_id}_used")

        with col3:
            st.markdown("**👥 Ownership**<br/><span style='font-size:12px; color:gray'>Is this device used only by you or shared?</span>", unsafe_allow_html=True)
            shared = st.selectbox("", ["Personal", "Shared"], index=["Personal", "Shared"].index(prev["shared"]), key=f"{device_id}_shared")

        with col4:
            st.markdown("**♻️ End-of-life behavior**<br/><span style='font-size:12px; color:gray'>What do you usually do when the device reaches its end of life?</span>", unsafe_allow_html=True)
            eol = st.selectbox("", list(eol_modifier.keys()), index=list(eol_modifier.keys()).index(prev["eol"]), key=f"{device_id}_eol")

        # --- UPDATE SESSION STATE ---
        st.session_state.device_inputs[device_id] = {
            "years": years,
            "used": used,
            "shared": shared,
            "eol": eol
        }

        # --- CALCOLO EMISSIONI ---
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

        # --- BOX CO2 ---
        st.markdown(f"""
            <div style="
                margin-top: 20px;
                background-color: #d8f3dc;
                padding: 12px 20px;
                border-radius: 10px;
                font-weight: 500;
                color: #1b4332;
            ">
                📊 Production: {prod_per_year:.2f} kg CO₂e/year &nbsp;&nbsp;&nbsp;
                ♻️ End-of-life: {eol_impact:.2f} kg CO₂e/year
            </div>
        """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)



    # === DIGITAL ACTIVITIES ===
    st.header("🎓 Digital Activities")

    st.markdown("""
        <div style="background-color: #f8fdfc; border-left: 6px solid #52b788;
                    padding: 20px 25px; border-radius: 12px; margin-bottom: 30px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.06);">
            <p style="font-size: 17px; margin-bottom: 0;">
                Estimate how many hours per day you spend on each activity during a typical 8-hour study or work day.  
                You may exceed 8 hours if multitasking (e.g., watching a lecture while writing notes).
            </p>
        </div>
    """, unsafe_allow_html=True)

    role = st.session_state.role
    ore_dict = {}
    digital_total = 0

    col1, col2 = st.columns(2)

    for i, (act, ef) in enumerate(activity_factors[role].items()):
        with (col1 if i % 2 == 0 else col2):
            st.markdown(f"""
                <div style="background-color: #e3fced; padding: 15px 20px; border-radius: 10px;
                            margin-bottom: 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.05);">
                    <label style="font-weight: 600; font-size: 16px;">{act} (h/day)</label>
            """, unsafe_allow_html=True)

            ore = st.slider("", min_value=0.0, max_value=8.0, value=0.0, step=0.5, key=act)
            st.markdown("</div>", unsafe_allow_html=True)
            ore_dict[act] = ore
            digital_total += ore * ef * DAYS

    # === HABITS BLOCK ===
    st.markdown("""
        <div style="background-color: #f8fdfc; border-left: 6px solid #52b788;
                    padding: 20px 25px; border-radius: 12px; margin-top: 30px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.06);">
            <p style="font-size: 17px; margin-bottom: 0;">
                Now tell us more about your habits related to email, cloud, printing and connectivity.
            </p>
        </div>
        <br>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📧 Emails without attachments**", unsafe_allow_html=True)
        email_plain = st.selectbox("", ["1–10", "11–20", "21–30", "31–40", "> 40"])

        st.markdown("**📎 Emails with attachments**", unsafe_allow_html=True)
        email_attach = st.selectbox("", ["1–10", "11–20", "21–30", "31–40", "> 40"])

    with col2:
        st.markdown("**☁️ Cloud Storage for academic/work files**", unsafe_allow_html=True)
        cloud = st.selectbox("", ["<5GB", "5–20GB", "20–50GB", "50–100GB"])

        st.markdown("**🖨️ Printed pages per day**", unsafe_allow_html=True)
        pages = st.number_input("", 0, 100, 0)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("""
        <div style="background-color: #e3fced; padding: 20px; border-radius: 10px; margin-bottom: 25px;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.05);">
            <label style="font-weight: 600; font-size: 16px;">📶 Daily Wi-Fi usage (hours)</label>
    """, unsafe_allow_html=True)

    wifi = st.slider("", 0.0, 8.0, 4.0, 0.5)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("""
        <div style="background-color: #e3fced; padding: 20px; border-radius: 10px;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.05);">
            <label style="font-weight: 600; font-size: 16px;">💻 When you're not using your computer...</label>
    """, unsafe_allow_html=True)

    idle = st.radio("", ["I turn it off", "I leave it on (idle mode)", "I don’t have a computer"])
    st.markdown("</div>", unsafe_allow_html=True)

    # === CALCOLI DIGITAL ACTIVITIES ===
    emails = {"1–10": 5, "11–20": 15, "21–30": 25, "31–40": 35, "> 40": 45}
    cloud_gb = {"<5GB": 3, "5–20GB": 13, "20–50GB": 35, "50–100GB": 75}

    mail_total = emails[email_plain] * 0.004 * DAYS + emails[email_attach] * 0.035 * DAYS + cloud_gb[cloud] * 0.01
    wifi_total = wifi * 0.00584 * DAYS
    print_total = pages * 0.0045 * DAYS

    if idle == "I leave it on (idle mode)":
        idle_total = DAYS * 0.0104 * 16
    elif idle == "I turn it off":
        idle_total = DAYS * 0.0005204 * 16
    else:
        idle_total = 0

    digital_total += mail_total + wifi_total + print_total + idle_total


    # === AI TOOLS ===
    st.header("🤖 AI Tools")

    st.markdown("""
        <div style="background-color: #f8fdfc; border-left: 6px solid #52b788;
                    padding: 20px 25px; border-radius: 12px; margin-bottom: 25px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.06);">
            <p style="font-size: 17px; margin-bottom: 0;">
                Estimate how many queries you make per day for each AI-powered task.
            </p>
        </div>
    """, unsafe_allow_html=True)

    ai_total = 0
    cols = st.columns(2)

    for i, (task, ef) in enumerate(ai_factors.items()):
        with cols[i % 2]:
            st.markdown(f"""
                <div style="background-color: #e3fced; padding: 20px 20px 10px 20px;
                            border-radius: 10px; margin-bottom: 20px;
                            box-shadow: 0 2px 6px rgba(0,0,0,0.05);">
                    <label style="font-weight: 600; font-size: 16px;">{task} (queries/day)</label>
            """, unsafe_allow_html=True)

            q = st.number_input("", 0, 100, 0, key=task)

            st.markdown("</div>", unsafe_allow_html=True)

            ai_total += q * ef * DAYS


    # === FINAL BUTTON ===
    st.markdown("""
        <div style="text-align: center; margin: 40px 0 20px 0;">
            <button style="
                background-color: #52b788;
                color: white;
                border: none;
                padding: 14px 28px;
                font-size: 18px;
                border-radius: 10px;
                cursor: pointer;
                font-weight: 600;
                transition: background-color 0.3s ease;
            " onmouseover="this.style.backgroundColor='#40916c'"
              onmouseout="this.style.backgroundColor='#52b788'">
                🌍 Discover Your Digital Carbon Footprint!
            </button>
        </div>
    """, unsafe_allow_html=True)

    # Simula il click del bottone Streamlit (funzionale)
    if st.button("🌍 Discover Your Digital Carbon Footprint!", key="trigger_logic"):
        st.session_state.results = {
            "Devices": total_prod,
            "E-Waste": total_eol,
            "Digital Activities": digital_total,
            "AI Tools": ai_total
        }
        st.session_state.page = "results"
        st.rerun()



def show_intro():
    import streamlit as st

    st.markdown("""
        <style>
        .intro-hero {
            background: linear-gradient(to right, #d8f3dc, #a8dadc);
            padding: 50px 30px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            margin-bottom: 30px;
        }
        .intro-title {
            font-size: 2.5em;
            margin-bottom: 0.2em;
            color: #1d3557;
        }
        .intro-subtitle {
            font-size: 1.1em;
            color: #1b4332;
        }
        .intro-body {
            background-color: #f1faee;
            padding: 30px;
            border-radius: 10px;
            max-width: 700px;
            margin: auto;
            font-size: 1.05em;
            color: #333;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        .select-label {
            margin-top: 1.5em;
            font-weight: 600;
        }
        .start-btn {
            background-color: #52b788;
            color: white;
            padding: 0.75em 1.5em;
            font-size: 1em;
            border-radius: 8px;
            border: none;
            margin-top: 20px;
            transition: all 0.2s ease;
        }
        .start-btn:hover {
            background-color: #40916c;
            cursor: pointer;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- HERO SECTION ---
    st.markdown("""
        <div class="intro-hero">
            <h1 class="intro-title">📱 Digital Carbon Footprint Calculator</h1>
            <p class="intro-subtitle">A Green DiLT initiative to raise awareness on digital sustainability in academia</p>
        </div>
    """, unsafe_allow_html=True)

    # --- CORPO TESTO ---
    st.markdown("""
        <div class="intro-body">
            Welcome to the <b>Digital Carbon Footprint Calculator</b>, a tool developed within the <i>Green DiLT</i> project to raise awareness about the hidden environmental impact of digital habits in academia.
            <br><br>
            This calculator is tailored for <b>university students, professors, and staff members</b>, helping you estimate your CO₂e emissions from everyday digital activities — often overlooked, but increasingly relevant.
            <hr style="margin: 1.5em 0;">
            👉 <b>Select your role to begin:</b>
        </div>
    """, unsafe_allow_html=True)

    # --- SELECTBOX ---
    st.session_state.role = st.selectbox(
        "What is your role in academia?",
        ["", "Student", "Professor", "Staff Member"]
    )

    # --- START BUTTON ---
    start = st.button("➡️ Start Calculation")

    if start:
        if st.session_state.role:
            st.session_state.page = "main"
            st.rerun()
        else:
            st.warning("Please select your role before continuing.")



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


