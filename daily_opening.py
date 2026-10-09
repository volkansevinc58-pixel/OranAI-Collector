import csv
from datetime import datetime, timedelta

MASTER = "collector_canli_master.csv"

OPENING_FIELDS = [
    "Tarih",
    "Saat",
    "EventID",
    "Organizasyon_Kodu",
    "Ev",
    "Deplasman",
    "Ilk_Gorulme_Zamani",
    "Ilk_MS1",
    "Ilk_MSX",
    "Ilk_MS2",
    "Ilk_KG_Var",
    "Ilk_KG_Yok",
    "Ilk_15_Alt",
    "Ilk_15_Ust",
    "Ilk_25_Alt",
    "Ilk_25_Ust",
    "Ilk_35_Alt",
    "Ilk_35_Ust",
]

simdi = datetime.now()
# 23:59 GitHub gorevi gece yarisi sonrasina sarkarsa ayni gunu hedefle.
if simdi.hour < 3:
    hedef_dt = simdi.date()
else:
    hedef_dt = simdi.date() + timedelta(days=1)

hedef_tarih = hedef_dt.strftime("%d.%m.%Y")
dosya_tarih = hedef_dt.strftime("%d_%m_%Y")

OUTPUT = f"oranai_{dosya_tarih}_ACILIS.csv"

rows = []

with open(
    MASTER,
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:

    reader = csv.DictReader(
        f,
        delimiter=";"
    )

    for row in reader:

        if (row.get("Guncel_Tarih") or row.get("Tarih")) != hedef_tarih:
            continue

        if not row.get("EventID"):
            continue

        rows.append({
            field: row.get(field, "")
            for field in OPENING_FIELDS
        })

rows.sort(
    key=lambda x: (
        x["Saat"],
        x["EventID"]
    )
)

with open(
    OUTPUT,
    "w",
    encoding="utf-8-sig",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=OPENING_FIELDS,
        delimiter=";"
    )

    writer.writeheader()
    writer.writerows(rows)

print("=" * 75)
print("ORAN AI - 23:59 GUNLUK ACILIS SNAPSHOT")
print("=" * 75)
print("Kayit zamani :", simdi.strftime("%d.%m.%Y %H:%M:%S"))
print("Hedef tarih  :", hedef_tarih)
print("Mac sayisi   :", len(rows))
print("Dosya        :", OUTPUT)
print("=" * 75)

