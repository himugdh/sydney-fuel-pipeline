# Is it worth the drive?
st.subheader("Is it worth the drive?")

postcode_list = run_query(
    r"""
    select distinct substring(address from '(\d{4})\s*$') as postcode
    from stations
    where address ~ '\d{4}\s*$' and latitude is not null
    order by 1
    """
)["postcode"].tolist()

c1, c2, c3, c4 = st.columns(4)
default_index = postcode_list.index("2000") if "2000" in postcode_list else 0
my_postcode = c1.selectbox("Your postcode", postcode_list, index=default_index)
radius = c2.slider("Search distance (km)", 1, 30, 10)
litres = c3.number_input("Litres to buy", min_value=5, max_value=120, value=40)
car_use = c4.number_input("Car use (L/100km)", min_value=3.0, max_value=25.0, value=9.0, step=0.5)

centre = run_query(
    r"""
    select avg(latitude) as lat, avg(longitude) as lng
    from stations
    where substring(address from '(\d{4})\s*$') = %s and latitude is not null
    """,
    (my_postcode,),
)

nearby = run_query(
    "select * from nearby_prices(%s, %s, %s, %s)",
    (float(centre["lat"].iloc[0]), float(centre["lng"].iloc[0]), fuel, float(radius)),
)

if nearby.empty:
    st.info("No stations with recent prices here. Try a bigger distance.")
else:
    ROAD_FACTOR = 1.3  # roads are longer than a straight line
    nearest = nearby.iloc[0]  # the list is sorted by distance

    extra_km = (nearby["distance_km"] - nearest["distance_km"]) * 2 * ROAD_FACTOR
    nearby["extra_km"] = extra_km.round(1)
    nearby["saving"] = (nearest["price"] - nearby["price"]) * litres / 100
    nearby["drive_cost"] = nearby["extra_km"] * car_use / 100 * nearby["price"] / 100
    nearby["net_saving"] = (nearby["saving"] - nearby["drive_cost"]).round(2)
    nearby["distance_km"] = nearby["distance_km"].round(1)

    nearby = nearby.sort_values("net_saving", ascending=False)
    best = nearby.iloc[0]

    if best["net_saving"] >= 1:
        st.success(
            f"Best pick: {best['name']}, {best['distance_km']} km away. "
            f"About \\${best['net_saving']:.2f} cheaper than the nearest station, "
            f"after petrol for the extra drive."
        )
    else:
        st.info(
            f"Not worth a detour. Filling up at {nearest['name']} "
            f"(the nearest station) is about as good as it gets."
        )

    left, right = st.columns([3, 2])
    left.dataframe(
        nearby.head(10)[
            ["name", "address", "price", "distance_km", "extra_km", "net_saving", "last_updated"]
        ],
        hide_index=True,
    )
    right.map(nearby.head(10)[["latitude", "longitude"]])
    st.caption(
        "Estimate only. Distance is a straight line times 1.3 to allow for roads. "
        "It ignores time and traffic, and hides prices older than 7 days. "
        "net_saving is in dollars, compared with filling up at the nearest station."
    )