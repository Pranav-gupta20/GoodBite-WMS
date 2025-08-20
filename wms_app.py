
# addming more recivers and providers
# Since you already have a users table and providers_data / receivers_data, you can insert new entries using SQL.
# For a new Provider
# Add provider info in providers_data:
# INSERT INTO providers_data (Name, Type, Address, City, Contact)
# VALUES ('Provider Name', 'Restaurant', 'Address here', 'City name', '1234567890');

# Add login credentials in users table, linking the new Provider_ID:

# INSERT INTO users (username, password, role, Provider_ID, Receiver_ID)
# VALUES ('providerusername', 'password123', 'Provider', NEW_PROVIDER_ID, NULL);
# Provider_ID = the ID you just inserted in providers_data
# Receiver_ID  = NULL
# For a new Receiver
# Add receiver info in receivers_data:

# INSERT INTO receivers_data (Name, Type, City, Contact)
# VALUES ('Receiver Name', 'Individual', 'City name', '9876543210');

# Add login credentials in users table, linking the new Receiver_ID:
# INSERT INTO users (username, password, role, Provider_ID, Receiver_ID)
# VALUES ('receiverusername', 'password123', 'Receiver', NULL, NEW_RECEIVER_ID);
# Provider_ID = NULL
#Receiver_ID = the ID you just inserted in receivers_data

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text

# ==========================
# CONFIG
# ==========================
st.set_page_config(page_title="GoodBite", page_icon="🍽️", layout="wide")

# ==========================
# DB
# ==========================
engine = create_engine(
    'mysql+pymysql://root:Pranav6096@127.0.0.1/wms',
    connect_args={'autocommit': True}
)

# ==========================
# HELPERS
# ==========================
def q(sql, params=None): #execute sql query and return DataFrame
    params = params or {}
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)

def exec_sql(sql, params=None):#it update data in database insert update delete
    params = params or {}
    with engine.connect() as conn:
        conn.execute(text(sql), params)

def metric_row(items):# display metrics in a row on the Streamlit dashboard.
    cols = st.columns(len(items))
    for c, (label, value) in zip(cols, items):
        with c:
            st.metric(label, value)

def filter_contains(df, col, value):#sed for search/filter functionality in your dashboard
    if df.empty or not value or col not in df.columns:
        return df
    return df[df[col].astype(str).str.contains(value.strip(), case=False, na=False)]

def sort_box(df, key=""):#Users can choose:Whether to sort ascending or descending
    if df.empty:
        return df
    left, right = st.columns([2,1])
    with left:
        by = st.selectbox("Sort by", df.columns.tolist(), key=f"sort_{key}_col")
    with right:
        asc = st.toggle("Ascending", value=True, key=f"sort_{key}_asc")
    return df.sort_values(by=by, ascending=asc)

# ==========================
# SESSION
# ==========================
def init_session():
    ss = st.session_state
    defaults = {
        "logged_in": False,
        "username": "",
        "role": "",
        "provider_id": None,
        "receiver_id": None,
        # NEW: allow Home buttons to navigate
        "_page_override": None,
    }
    for k, v in defaults.items():
        if k not in ss:
            ss[k] = v

init_session()

def login_user(u, r, pid=None, rid=None):
    st.session_state.logged_in = True
    st.session_state.username = u
    st.session_state.role = r
    st.session_state.provider_id = pid
    st.session_state.receiver_id = rid

def logout_user():
    for k in ["logged_in", "username", "role", "provider_id", "receiver_id"]:
        if k == "logged_in":
            st.session_state[k] = False
        else:
            st.session_state[k] = None if k.endswith("_id") else ""
    st.session_state._page_override = None

# helper to jump pages from Home
def go_to(target: str):
    st.session_state._page_override = target
    st.rerun()

# ==========================
# NAV
# ==========================
if st.session_state.logged_in:
    st.sidebar.title(f"Welcome, {st.session_state.username} 👋")
    st.sidebar.caption(f"Role: **{st.session_state.role}**")
    if st.session_state.role == "Admin":
        page = st.sidebar.radio("Go to:", ["Home", "Provider Dashboard", "Receiver Dashboard", "Admin Dashboard"])
    elif st.session_state.role == "Provider":
        page = "Provider Dashboard"
    elif st.session_state.role == "Receiver":
        page = "Receiver Dashboard"
    else:
        page = "Home"
    if st.sidebar.button("Logout"):
        logout_user()
        st.rerun()
else:
    page = "Home"

# apply any Home button override
if st.session_state.get("_page_override"):
    page = st.session_state._page_override
    st.session_state._page_override = None

# ==========================
# HOME (IMPROVED)
# ==========================
st.title("Welcome to GoodBite 🍽️")
st.caption("Turning surplus into smiles")

# --- Hero / Quick actions ---
if st.session_state.logged_in:
    st.subheader("Quick actions")
    c1, c2, c3 = st.columns(3)
    role = st.session_state.role

    with c1:
        if role in ["Admin", "Provider"]:
            if st.button("📦 Open Provider Dashboard", use_container_width=True):
                go_to("Provider Dashboard")
        else:
            st.write("")
    with c2:
        if role in ["Admin", "Receiver"]:
            if st.button("🙋 Open Receiver Dashboard", use_container_width=True):
                go_to("Receiver Dashboard")
        else:
            st.write("")
    with c3:
        if role == "Admin":
            if st.button("🛠️ Open Admin Dashboard", use_container_width=True):
                go_to("Admin Dashboard")
        else:
            st.write("")
else:
    # Not logged in: show login form + preview buttons do nothing (disabled)
    st.info("Log in to access your dashboard.")
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            row = None
            with engine.connect() as conn:
                row = conn.execute(text("""
                    SELECT username, role, password, Provider_ID, Receiver_ID
                    FROM users
                    WHERE LOWER(username) = :u
                """), {"u": u.strip().lower()}).fetchone()
            if row and p == row.password:
                login_user(row.username, row.role.capitalize(), row.Provider_ID, row.Receiver_ID)
                st.rerun()
            else:
                st.error("Invalid username or password")

# --- Live stats (global) ---
st.markdown("### Live stats")
try:
    providers = q("SELECT COUNT(*) c FROM providers_data").iloc[0,0]
    receivers = q("SELECT COUNT(*) c FROM receivers_data").iloc[0,0]
    active_listings = q("""
        SELECT COUNT(*) c
        FROM food_listings_data
        WHERE Quantity > 0 AND Expiry_Date >= CURDATE()
    """).iloc[0,0]
    active_claims = q("""
        SELECT COUNT(*) c
        FROM claims_data
        WHERE LOWER(TRIM(Status)) IN ('pending','approved')
    """).iloc[0,0]
except Exception as e:
    providers = receivers = active_listings = active_claims = 0
    st.warning(f"Could not load global stats: {e}")

metric_row([
    ("Providers", providers),
    ("Receivers", receivers),
    ("Active Listings", active_listings),
    ("Active Claims", active_claims),
])

# --- Role-aware mini-stats ---
if st.session_state.logged_in:
    if role == "Provider" and st.session_state.provider_id is not None:
        pid = st.session_state.provider_id
        p_pending = q("""
            SELECT COUNT(*) c FROM claims_data c
            JOIN food_listings_data f ON c.Food_ID = f.Food_ID
            WHERE f.Provider_ID = :pid AND LOWER(TRIM(c.Status))='pending'
        """, {"pid": pid}).iloc[0,0]
        p_qty = q("""
            SELECT COALESCE(SUM(Quantity),0) s FROM food_listings_data
            WHERE Provider_ID = :pid
        """, {"pid": pid}).iloc[0,0]
        metric_row([("My Pending Claims", p_pending), ("My Total Stock (qty)", int(p_qty))])

    if role == "Receiver" and st.session_state.receiver_id is not None:
        rid = st.session_state.receiver_id
        r_pending = q("""
            SELECT COUNT(*) c FROM claims_data
            WHERE Receiver_ID = :rid AND LOWER(TRIM(Status))='pending'
        """, {"rid": rid}).iloc[0,0]
        r_total = q("""
            SELECT COUNT(*) c FROM claims_data
            WHERE Receiver_ID = :rid
        """, {"rid": rid}).iloc[0,0]
        metric_row([("My Pending Claims", r_pending), ("My Total Claims", r_total)])

st.markdown("---")

# --- Recent Activity (role-aware) ---
st.subheader("Recent activity")

colA, colB = st.columns(2)

with colA:
    st.markdown("**Latest food listings**")
    try:
        if st.session_state.logged_in and role == "Provider" and st.session_state.provider_id is not None:
            latest_listings = q("""
                SELECT Food_ID, Food_Name, Quantity, Expiry_Date, Food_Type, Meal_Type
                FROM food_listings_data
                WHERE Provider_ID = :pid
                ORDER BY Food_ID DESC
                LIMIT 8
            """, {"pid": st.session_state.provider_id})
        else:
            latest_listings = q("""
                SELECT f.Food_ID, f.Food_Name, f.Quantity, f.Expiry_Date, f.Food_Type, f.Meal_Type, p.Name AS Provider
                FROM food_listings_data f
                JOIN providers_data p ON f.Provider_ID = p.Provider_ID
                WHERE f.Quantity > 0 AND f.Expiry_Date >= CURDATE()
                ORDER BY f.Food_ID DESC
                LIMIT 8
            """)
    except Exception as e:
        latest_listings = pd.DataFrame()
        st.warning(f"Could not load listings: {e}")

    if latest_listings.empty:
        st.write("No recent listings.")
    else:
        st.dataframe(latest_listings, use_container_width=True, height=270)

with colB:
    st.markdown("**Latest claims**")
    try:
        if st.session_state.logged_in and role == "Provider" and st.session_state.provider_id is not None:
            latest_claims = q("""
                SELECT c.Claim_ID, f.Food_Name, r.Name AS Receiver, c.Status, c.Timestamp
                FROM claims_data c
                JOIN food_listings_data f ON c.Food_ID = f.Food_ID
                JOIN receivers_data r ON c.Receiver_ID = r.Receiver_ID
                WHERE f.Provider_ID = :pid
                ORDER BY c.Timestamp DESC
                LIMIT 8
            """, {"pid": st.session_state.provider_id})
        elif st.session_state.logged_in and role == "Receiver" and st.session_state.receiver_id is not None:
            latest_claims = q("""
                SELECT c.Claim_ID, f.Food_Name, c.Status, c.Timestamp
                FROM claims_data c
                JOIN food_listings_data f ON c.Food_ID = f.Food_ID
                WHERE c.Receiver_ID = :rid
                ORDER BY c.Timestamp DESC
                LIMIT 8
            """, {"rid": st.session_state.receiver_id})
        else:
            latest_claims = q("""
                SELECT c.Claim_ID, f.Food_Name, r.Name AS Receiver, p.Name AS Provider, c.Status, c.Timestamp
                FROM claims_data c
                JOIN food_listings_data f ON c.Food_ID = f.Food_ID
                JOIN receivers_data r ON c.Receiver_ID = r.Receiver_ID
                JOIN providers_data p ON f.Provider_ID = p.Provider_ID
                ORDER BY c.Timestamp DESC
                LIMIT 8
            """)
    except Exception as e:
        latest_claims = pd.DataFrame()
        st.warning(f"Could not load claims: {e}")

    if latest_claims.empty:
        st.write("No recent claims.")
    else:
        st.dataframe(latest_claims, use_container_width=True, height=270)

# --- How it works ---
with st.expander("How it works (quick guide)"):
    st.markdown("""
1. **Providers** add surplus food with quantity, type, and expiry.
2. **Receivers** browse available items and place a **claim**.
3. **Providers** **Approve/Reject** pending claims.
4. On **approval**, the item’s quantity is decremented automatically.
5. **Admins** can view analytics, directories, and add users.
""")

# ==========================
# PROVIDER DASHBOARD
# ==========================
if page == "Provider Dashboard" and st.session_state.role in ["Provider", "Admin"]:
    st.header("📦 Provider Dashboard")
    pid = st.session_state.provider_id

    if st.session_state.role == "Admin":
        prov = q("SELECT Provider_ID, Name, City FROM providers_data ORDER BY Name")
        if not prov.empty:
            display = prov.apply(lambda r: f"{int(r['Provider_ID'])} — {r['Name']} ({r['City']})", axis=1)
            pick = st.selectbox("Manage Provider", display)
            pid = int(pick.split(" — ")[0])

    if pid is None:
        st.info("Choose a provider (Admin) or login as Provider.")
    else:
        listings = q("""
            SELECT Food_ID, Food_Name, Quantity, Expiry_Date, Food_Type, Meal_Type
            FROM food_listings_data WHERE Provider_ID = :pid
        """, {"pid": pid})

        claims_all = q("""
            SELECT c.Claim_ID, c.Status
            FROM claims_data c
            JOIN food_listings_data f ON c.Food_ID = f.Food_ID
            WHERE f.Provider_ID = :pid
        """, {"pid": pid})
        pend = (claims_all['Status'].str.lower() == 'pending').sum() if not claims_all.empty else 0
        appr = (claims_all['Status'].str.lower() == 'approved').sum() if not claims_all.empty else 0
        qty_sum = listings['Quantity'].sum() if not listings.empty else 0

        st.subheader("Overview")
        metric_row([
            ("Total Listings", len(listings)),
            ("Total Quantity", qty_sum),
            ("Pending Claims", pend),
            ("Approved Claims", appr),
        ])

        with st.expander("Food Listings", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1: f_name = st.text_input("Food Name contains")
            with c2: f_type = st.text_input("Food Type contains")
            with c3: f_meal = st.text_input("Meal Type contains")
            with c4: f_from = st.date_input("Expiry From", value=None)

            df = listings.copy()
            df = filter_contains(df, "Food_Name", f_name)
            df = filter_contains(df, "Food_Type", f_type)
            df = filter_contains(df, "Meal_Type", f_meal)
            if f_from:
                df = df[df["Expiry_Date"] >= pd.to_datetime(f_from)]
            df = sort_box(df, key="prov_list")
            st.dataframe(df, use_container_width=True)

        with st.expander("Add New Food Listing", expanded=True):
            with st.form("add_food"):
                fn = st.text_input("Food Name")
                qty = st.number_input("Quantity", min_value=1, step=1)
                exp = st.date_input("Expiry Date")
                ft = st.selectbox("Food Type", ["Vegetables", "Fruits", "Dairy", "Grains", "Other"])
                mt = st.selectbox("Meal Type", ["Breakfast", "Lunch", "Dinner", "Snack", "Other"])
                if st.form_submit_button("Add"):
                    if not fn.strip():
                        st.error("Enter a valid food name.")
                    else:
                        exec_sql("""INSERT INTO food_listings_data
                                    (Food_Name, Quantity, Expiry_Date, Food_Type, Meal_Type, Provider_ID)
                                    VALUES (:fn, :q, :e, :ft, :mt, :pid)""",
                                {"fn": fn.strip(), "q": qty, "e": exp, "ft": ft, "mt": mt, "pid": pid})
                        st.success(f"Added '{fn}'")
                        st.rerun()

        st.subheader("Claims")
        cdf = q("""
            SELECT c.Claim_ID, c.Food_ID, f.Food_Name, r.Name AS Receiver_Name, c.Status, c.Timestamp
            FROM claims_data c
            JOIN food_listings_data f ON c.Food_ID = f.Food_ID
            JOIN receivers_data r ON c.Receiver_ID = r.Receiver_ID
            WHERE f.Provider_ID = :pid ORDER BY c.Timestamp DESC
        """, {"pid": pid})
        if cdf.empty:
            st.info("No claims yet.")
        else:
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                sel_status = st.multiselect("Status", sorted(cdf['Status'].str.capitalize().unique()),
                                            default=sorted(cdf['Status'].str.capitalize().unique()))
            with cc2:
                s_food = st.text_input("Food Name contains", key="provider_food_search")
            with cc3:
                s_recv = st.text_input("Receiver Name contains")
            cdf["StatusCap"] = cdf["Status"].str.capitalize()
            cdf2 = cdf[cdf["StatusCap"].isin(sel_status)].drop(columns=["StatusCap"])
            cdf2 = filter_contains(cdf2, "Food_Name", s_food)
            cdf2 = filter_contains(cdf2, "Receiver_Name", s_recv)
            cdf2 = sort_box(cdf2, key="prov_claims")
            st.dataframe(cdf2, use_container_width=True)

            pend_df = cdf[cdf["Status"].str.lower() == "pending"]
            if not pend_df.empty:
                with st.form("manage_claim"):
                    cid = st.selectbox("Pending Claim", pend_df["Claim_ID"])
                    action = st.radio("Action", ["Approve", "Reject"], horizontal=True)
                    if st.form_submit_button("Submit"):
                        new_s = action.lower()
                        exec_sql("UPDATE claims_data SET Status = :s WHERE Claim_ID = :c", {"s": new_s, "c": int(cid)})
                        if new_s == "approved":
                            fid = int(pend_df.loc[pend_df["Claim_ID"] == cid, "Food_ID"].values[0])
                            exec_sql("""UPDATE food_listings_data
                                        SET Quantity = Quantity - 1
                                        WHERE Food_ID = :f AND Quantity > 0""", {"f": fid})
                        st.success(f"Claim {action}!")
                        st.rerun()

# ==========================
# RECEIVER DASHBOARD
# ==========================
if page == "Receiver Dashboard" and st.session_state.role in ["Receiver", "Admin"]:
    st.header("🙋 Receiver Dashboard")
    rid = st.session_state.receiver_id

    if st.session_state.role == "Admin":
        rc = q("SELECT Receiver_ID, Name, City FROM receivers_data ORDER BY Name")
        if not rc.empty:
            show = rc.apply(lambda r: f"{int(r['Receiver_ID'])} — {r['Name']} ({r['City']})", axis=1)
            pick = st.selectbox("View Receiver", show)
            rid = int(pick.split(" — ")[0])

    if rid is None:
        st.info("Choose a receiver (Admin) or login as Receiver.")
    else:
        my_all = q("SELECT Claim_ID, Status FROM claims_data WHERE Receiver_ID = :r", {"r": rid})
        rp = (my_all['Status'].str.lower() == 'pending').sum() if not my_all.empty else 0
        ra = (my_all['Status'].str.lower() == 'approved').sum() if not my_all.empty else 0
        rr = (my_all['Status'].str.lower() == 'rejected').sum() if not my_all.empty else 0

        st.subheader("Overview")
        metric_row([
            ("My Total Claims", len(my_all)),
            ("Pending", rp),
            ("Approved", ra),
            ("Rejected", rr),
        ])

        avail = q("""
            SELECT f.Food_ID, f.Food_Name, f.Quantity, f.Expiry_Date, f.Food_Type, f.Meal_Type, p.City AS Provider_City
            FROM food_listings_data f
            JOIN providers_data p ON f.Provider_ID = p.Provider_ID
            WHERE f.Quantity > 0 AND f.Expiry_Date >= CURDATE()
            AND f.Food_ID NOT IN (SELECT Food_ID FROM claims_data WHERE Receiver_ID = :r)
            ORDER BY f.Expiry_Date ASC
        """, {"r": rid})

        with st.expander("Available Food", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1: a_city = st.text_input("City contains")
            with c2: a_food = st.text_input("Food contains")
            with c3: a_type = st.text_input("Type contains")
            with c4: a_meal = st.text_input("Meal contains")
            af = avail.copy()
            af = filter_contains(af, "Provider_City", a_city)
            af = filter_contains(af, "Food_Name", a_food)
            af = filter_contains(af, "Food_Type", a_type)
            af = filter_contains(af, "Meal_Type", a_meal)
            af = sort_box(af, key="recv_avail")
            st.dataframe(af, use_container_width=True)

            with st.form("claim_food"):
                choices = af["Food_ID"].tolist() if not af.empty else []
                fid = st.selectbox("Select Food", choices)

                if st.form_submit_button("Claim"):
                    if fid:  # only proceed if something is selected
                        exec_sql("""INSERT INTO claims_data (Food_ID, Receiver_ID, Status, Timestamp)
                                    VALUES (:f, :r, 'pending', NOW())""",
                                    {"f": int(fid), "r": rid})
                        st.success("✅ Claim sent!")
                        st.rerun()
                    else:
                        st.warning("⚠️ No food available to claim.")


        mine = q("""
            SELECT f.Food_ID, f.Food_Name, c.Status, f.Quantity, f.Expiry_Date, f.Food_Type, f.Meal_Type, p.City AS Provider_City, c.Timestamp
            FROM claims_data c
            JOIN food_listings_data f ON c.Food_ID = f.Food_ID
            JOIN providers_data p ON f.Provider_ID = p.Provider_ID
            WHERE c.Receiver_ID = :r ORDER BY c.Timestamp DESC
        """, {"r": rid})

        with st.expander("My Claims", expanded=True):
            if mine.empty:
                st.info("No claims yet.")
            else:
                c1, c2, c3 = st.columns(3)
                with c1:
                    sel = st.multiselect("Status",
                                            sorted(mine["Status"].str.capitalize().unique()),
                                            default=sorted(mine["Status"].str.capitalize().unique()))
                with c2:
                    nf = st.text_input("Food contains", key="receiver_claim_food_search")
                with c3:
                    nc = st.text_input("Provider City contains")
                m = mine.copy()
                m["S"] = m["Status"].str.capitalize()
                m = m[m["S"].isin(sel)].drop(columns=["S"])
                m = filter_contains(m, "Food_Name", nf)
                m = filter_contains(m, "Provider_City", nc)
                m = sort_box(m, key="recv_mine")
                st.dataframe(m, use_container_width=True)

# ==========================
# ADMIN DASHBOARD
# ==========================
if page == "Admin Dashboard" and st.session_state.role == "Admin":
    st.header("🛠️ Admin Dashboard")

    pc = q("SELECT COUNT(*) c FROM providers_data").iloc[0,0]
    rc = q("SELECT COUNT(*) c FROM receivers_data").iloc[0,0]
    fc = q("SELECT COUNT(*) c FROM food_listings_data").iloc[0,0]
    cc = q("SELECT COUNT(*) c FROM claims_data").iloc[0,0]
    metric_row([("Providers", pc), ("Receivers", rc), ("Food Listings", fc), ("Total Claims", cc)])

    stat = q("SELECT LOWER(TRIM(Status)) s, COUNT(*) c FROM claims_data GROUP BY LOWER(TRIM(Status))")
    p = int(stat.loc[stat["s"]=="pending","c"].sum()) if not stat.empty else 0
    a = int(stat.loc[stat["s"]=="approved","c"].sum()) if not stat.empty else 0
    r = int(stat.loc[stat["s"]=="rejected","c"].sum()) if not stat.empty else 0
    metric_row([("Pending", p), ("Approved", a), ("Rejected", r)])

    st.markdown("---")
    st.subheader("Claims Analytics")
    d = q("""
        SELECT f.Food_ID, f.Food_Name, f.Quantity, COUNT(c.Claim_ID) AS Number_of_Claims
        FROM claims_data c
        JOIN food_listings_data f ON c.Food_ID = f.Food_ID
        GROUP BY f.Food_ID, f.Food_Name, f.Quantity
        ORDER BY Number_of_Claims DESC
    """)
    left, right = st.columns([2,3])
    with left: st.dataframe(d, use_container_width=True)
    with right:
        if not d.empty:
            kind = st.selectbox("Chart", ["Histogram", "Bar Chart - Claims", "Bar Chart - Quantity"])
            if kind == "Histogram":
                fig, ax = plt.subplots()
                ax.hist(d["Number_of_Claims"], bins=10, color='skyblue', edgecolor='black')
                ax.set_xlabel("Number of Claims"); ax.set_ylabel("Frequency")
                st.pyplot(fig)
            elif kind == "Bar Chart - Claims":
                st.bar_chart(d.set_index("Food_Name")["Number_of_Claims"])
            else:
                st.bar_chart(d.set_index("Food_Name")["Quantity"])
        else:
            st.info("No claims found.")

    st.markdown("---")
    st.subheader("Directories")
    tabs = st.tabs(["Providers", "Receivers"])
    with tabs[0]:
        df = q("SELECT Provider_ID, Name, Type, City, Contact FROM providers_data ORDER BY Provider_ID DESC")
        n = st.text_input("Name contains", key="ap1")
        c = st.text_input("City contains", key="ap2")
        t = st.text_input("Type contains", key="ap3")
        df = filter_contains(df, "Name", n)
        df = filter_contains(df, "City", c)
        df = filter_contains(df, "Type", t)
        df = sort_box(df, key="ap")
        st.dataframe(df, use_container_width=True)
    with tabs[1]:
        rf = q("SELECT Receiver_ID, Name, Type, City, Contact FROM receivers_data ORDER BY Receiver_ID DESC")
        n = st.text_input("Name contains", key="ar1")
        c = st.text_input("City contains", key="ar2")
        t = st.text_input("Type contains", key="ar3")
        rf = filter_contains(rf, "Name", n)
        rf = filter_contains(rf, "City", c)
        rf = filter_contains(rf, "Type", t)
        rf = sort_box(rf, key="ar")
        st.dataframe(rf, use_container_width=True)

    st.markdown("---")
    st.subheader("➕ Add New User")
    with st.form("add_user"):
        role_sel = st.selectbox("Role", ["Provider", "Receiver"])
        name = st.text_input("Name")
        typ = st.text_input("Type")
        city = st.text_input("City")
        contact = st.text_input("Contact")
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Add User"):
            if not all([name.strip(), typ.strip(), city.strip(), contact.strip(), user.strip(), pwd.strip()]):
                st.error("Fill all fields.")
            else:
                if role_sel == "Provider":
                    exec_sql("""INSERT INTO providers_data (Name, Type, Address, City, Contact)
                                VALUES (:n, :t, '', :c, :p)""",
                                {"n": name.strip(), "t": typ.strip(), "c": city.strip(), "p": contact.strip()})
                    pid = q("SELECT LAST_INSERT_ID() id").iloc[0,0]
                    exec_sql("""INSERT INTO users (username, password, role, Provider_ID, Receiver_ID)
                                VALUES (:u, :pw, 'Provider', :pid, NULL)""",
                                {"u": user.strip(), "pw": pwd.strip(), "pid": pid})
                else:
                    exec_sql("""INSERT INTO receivers_data (Name, Type, City, Contact)
                                VALUES (:n, :t, :c, :p)""",
                                {"n": name.strip(), "t": typ.strip(), "c": city.strip(), "p": contact.strip()})
                    rid = q("SELECT LAST_INSERT_ID() id").iloc[0,0]
                    exec_sql("""INSERT INTO users (username, password, role, Provider_ID, Receiver_ID)
                                VALUES (:u, :pw, 'Receiver', NULL, :rid)""",
                                {"u": user.strip(), "pw": pwd.strip(), "rid": rid})
                st.success(f"{role_sel} '{name}' added!")
                st.rerun() 