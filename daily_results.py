# -*- coding: utf-8 -*-

import requests
import csv
import re
from datetime import datetime, timedelta

URL = "https://arsiv.mackolik.com/AjaxHandlers/ProgramDataHandler.ashx"
MASTER_CSV = "collector_canli_master.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    ),
    "Referer": "https://arsiv.mackolik.com/Genis-Iddaa-Programi",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "*/*"
}


def temizle(v):
    return str(v).strip().strip("'\"")


def oran(v):
    v = temizle(v).replace(",", ".")

    if not v:
        return ""

    try:
        x = float(v)

        if x <= 0:
            return ""

        return str(x)

    except:
        return ""


def sayi(v):
    v = temizle(v)

    try:
        return int(float(v))
    except:
        return None


def master_oku():
    sonuc = {}
    try:
        with open(MASTER_CSV, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                eid = str(row.get("EventID", "")).strip()
                if eid:
                    sonuc[eid] = row
    except FileNotFoundError:
        print("MASTER BULUNAMADI:", MASTER_CSV)
    return sonuc

def alanlara_ayir(record):
    content = record[1:-1]

    fields = []
    current = []
    quote = None
    escape = False
    depth = 0

    for ch in content:

        if quote is not None:
            current.append(ch)

            if escape:
                escape = False
                continue

            if ch == "\\":
                escape = True
                continue

            if ch == quote:
                quote = None

            continue

        if ch in ("'", '"'):
            quote = ch
            current.append(ch)

        elif ch in "[{(":
            depth += 1
            current.append(ch)

        elif ch in "]})":
            depth -= 1
            current.append(ch)

        elif ch == "," and depth == 0:
            fields.append(
                "".join(current).strip()
            )
            current = []

        else:
            current.append(ch)

    fields.append(
        "".join(current).strip()
    )

    return fields


def arrayleri_bul(text):
    sonuc = []

    quote = None
    escape = False
    stack = []

    for i, ch in enumerate(text):

        if quote is not None:

            if escape:
                escape = False
                continue

            if ch == "\\":
                escape = True
                continue

            if ch == quote:
                quote = None

            continue

        if ch in ("'", '"'):
            quote = ch
            continue

        if ch == "[":
            stack.append(i)

        elif ch == "]" and stack:
            start = stack.pop()

            sonuc.append(
                text[start:i + 1]
            )

    return sonuc


def veri_cek(day, sort_dir, np_value):
    params = {
        "type": 6,
        "sortValue": "DATE",
        "day": day,
        "sort": -1,
        "sortDir": sort_dir,
        "groupId": -1,
        "np": np_value,
        "sport": 1
    }

    r = requests.get(
        URL,
        params=params,
        headers=HEADERS,
        timeout=30
    )

    r.raise_for_status()

    return r.text


def maclari_bul(raw, hedef_tarih):
    sonuc = {}

    for arr in arrayleri_bul(raw):

        if hedef_tarih not in arr:
            continue

        if not re.match(
            r"^\[\s*\d+\s*,",
            arr
        ):
            continue

        fields = alanlara_ayir(arr)

        if len(fields) <= 50:
            continue

        if temizle(fields[7]) != hedef_tarih:
            continue

        eid = temizle(fields[50])

        if not eid:
            continue

        sonuc[eid] = fields

    return sonuc


def gunu_cek(tarih_dt):
    hedef = tarih_dt.strftime("%d.%m.%Y")

    onceki = (
        tarih_dt - timedelta(days=1)
    ).strftime("%d.%m.%Y")

    raw_a = veri_cek(
        hedef,
        1,
        -1
    )

    A = maclari_bul(
        raw_a,
        hedef
    )

    raw_b = veri_cek(
        onceki,
        -1,
        1
    )

    B = maclari_bul(
        raw_b,
        hedef
    )

    tum = dict(A)

    for eid, fields in B.items():
        if eid not in tum:
            tum[eid] = fields

    return (
        tum,
        raw_a,
        raw_b,
        len(A),
        len(B)
    )


def sonuc_hesapla(ev_gol, dep_gol):
    toplam = ev_gol + dep_gol

    if ev_gol > dep_gol:
        ms = "1"

    elif ev_gol < dep_gol:
        ms = "2"

    else:
        ms = "X"

    if ev_gol > 0 and dep_gol > 0:
        kg = "VAR"
    else:
        kg = "YOK"

    s15 = "UST" if toplam > 1.5 else "ALT"
    s25 = "UST" if toplam > 2.5 else "ALT"
    s35 = "UST" if toplam > 3.5 else "ALT"

    return (
        ms,
        kg,
        s15,
        s25,
        s35,
        toplam
    )



def kalite_kontrol(eid, sonuc_row, master, hedef_tarih):
    master_row = master.get(eid)
    if master_row is None:
        return False, "MASTERDA_YOK"

    master_tarih = (
        master_row.get("Guncel_Tarih")
        or master_row.get("Tarih", "")
    ).strip()

    if master_tarih != hedef_tarih:
        return False, "TARIH_UYUSMAZ"

    master_ev = temizle(master_row.get("Ev", ""))
    master_dep = temizle(master_row.get("Deplasman", ""))
    sonuc_ev = temizle(sonuc_row.get("Ev", ""))
    sonuc_dep = temizle(sonuc_row.get("Deplasman", ""))

    if master_ev != sonuc_ev or master_dep != sonuc_dep:
        return False, "TAKIM_UYUSMAZ"

    return True, "ONAYLI"



FINAL_FIELDS = [
    "Tarih",
    "Saat",
    "EventID",
    "Ev",
    "Deplasman",

    "Kapanis_MS1",
    "Kapanis_MSX",
    "Kapanis_MS2",

    "Kapanis_KG_Var",
    "Kapanis_KG_Yok",

    "Kapanis_15_Alt",
    "Kapanis_15_Ust",

    "Kapanis_25_Alt",
    "Kapanis_25_Ust",

    "Kapanis_35_Alt",
    "Kapanis_35_Ust",

    "Ev_Gol",
    "Dep_Gol",

    "MS_Sonuc",
    "KG_Sonuc",

    "Sonuc_15",
    "Sonuc_25",
    "Sonuc_35",

    "Toplam_Gol",
    "Mac_Durum",
    "Sonuc_Kayit_Zamani"
]


def tarihi_isle(tarih_dt, simdi):
    HEDEF_TARIH = tarih_dt.strftime(
        "%d.%m.%Y"
    )

    DOSYA_TARIH = tarih_dt.strftime(
        "%d_%m_%Y"
    )

    RAW_A = (
        f"mackolik_{DOSYA_TARIH}"
        "_SONUC_A_raw.txt"
    )

    RAW_B = (
        f"mackolik_{DOSYA_TARIH}"
        "_SONUC_B_raw.txt"
    )

    RAW_MERGED = (
        f"mackolik_{DOSYA_TARIH}"
        "_SONUC_raw.txt"
    )

    FINAL_CSV = (
        f"oranai_{DOSYA_TARIH}"
        "_SONUC_GUVENLI.csv"
    )

    print()
    print("=" * 75)
    print("HEDEF TARIH :", HEDEF_TARIH)
    print("=" * 75)

    try:
        (
            maclar,
            raw_a,
            raw_b,
            a_sayi,
            b_sayi
        ) = gunu_cek(tarih_dt)

    except Exception as e:
        print(
            "CEKIM HATASI:",
            e
        )

        return False

    print(
        "A EventID      :",
        a_sayi
    )

    print(
        "B EventID      :",
        b_sayi
    )

    print(
        "Benzersiz RAW  :",
        len(maclar)
    )

    # ---------------------------------------
    # RAW DOSYALARI
    # ---------------------------------------

    with open(
        RAW_A,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(raw_a)

    with open(
        RAW_B,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(raw_b)

    with open(
        RAW_MERGED,
        "w",
        encoding="utf-8"
    ) as f:

        f.write("var m = [\n")

        for fields in maclar.values():

            f.write(
                "["
                + ",".join(fields)
                + "],\n"
            )

        f.write("];")

    # ---------------------------------------
    # SADECE STATUS=4
    # ---------------------------------------

    final_rows = {}
    durum_sayac = {}

    for eid, fields in maclar.items():

        durum = temizle(
            fields[5]
        )

        durum_sayac[durum] = (
            durum_sayac.get(
                durum,
                0
            ) + 1
        )

        if durum != "4":
            continue

        ev_gol = sayi(
            fields[8]
        )

        dep_gol = sayi(
            fields[9]
        )

        if (
            ev_gol is None
            or dep_gol is None
        ):
            continue

        (
            ms,
            kg,
            s15,
            s25,
            s35,
            toplam
        ) = sonuc_hesapla(
            ev_gol,
            dep_gol
        )

        final_rows[eid] = {

            "Tarih":
                temizle(fields[7]),

            "Saat":
                temizle(fields[6]),

            "EventID":
                eid,

            "Ev":
                temizle(fields[1]),

            "Deplasman":
                temizle(fields[3]),

            "Kapanis_MS1":
                oran(fields[16]),

            "Kapanis_MSX":
                oran(fields[17]),

            "Kapanis_MS2":
                oran(fields[18]),

            "Kapanis_KG_Var":
                oran(fields[39]),

            "Kapanis_KG_Yok":
                oran(fields[40]),

            "Kapanis_15_Alt":
                oran(fields[44]),

            "Kapanis_15_Ust":
                oran(fields[45]),

            "Kapanis_25_Alt":
                oran(fields[22]),

            "Kapanis_25_Ust":
                oran(fields[23]),

            "Kapanis_35_Alt":
                oran(fields[46]),

            "Kapanis_35_Ust":
                oran(fields[47]),

            "Ev_Gol":
                ev_gol,

            "Dep_Gol":
                dep_gol,

            "MS_Sonuc":
                ms,

            "KG_Sonuc":
                kg,

            "Sonuc_15":
                s15,

            "Sonuc_25":
                s25,

            "Sonuc_35":
                s35,

            "Toplam_Gol":
                toplam,

            "Mac_Durum":
                durum,

            "Sonuc_Kayit_Zamani":
                simdi.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
        }


    master = master_oku()
    onayli_rows = {}
    reddedilen_rows = {}
    kalite_sayac = {}

    for eid, row in final_rows.items():
        uygun, neden = kalite_kontrol(
            eid, row, master, HEDEF_TARIH
        )
        kalite_sayac[neden] = kalite_sayac.get(neden, 0) + 1

        if uygun:
            onayli_rows[eid] = row
        else:
            reddedilen_rows[eid] = (row, neden)

    final_rows = onayli_rows

    with open(
        FINAL_CSV,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=FINAL_FIELDS,
            delimiter=";"
        )

        writer.writeheader()

        for row in sorted(
            final_rows.values(),
            key=lambda x: (
                x["Saat"],
                x["EventID"]
            )
        ):
            writer.writerow(row)


    KALITE_RED_CSV = (
        f"oranai_{DOSYA_TARIH}"
        "_KALITE_RED.csv"
    )

    with open(
        KALITE_RED_CSV,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        kalite_fields = [
            "Tarih", "Saat", "EventID",
            "Ev", "Deplasman", "Ret_Nedeni"
        ]
        writer = csv.DictWriter(
            f,
            fieldnames=kalite_fields,
            delimiter=";"
        )
        writer.writeheader()

        for row, neden in sorted(
            reddedilen_rows.values(),
            key=lambda x: (x[0].get("Saat", ""), x[0].get("EventID", ""))
        ):
            writer.writerow({
                "Tarih": row.get("Tarih", ""),
                "Saat": row.get("Saat", ""),
                "EventID": row.get("EventID", ""),
                "Ev": row.get("Ev", ""),
                "Deplasman": row.get("Deplasman", ""),
                "Ret_Nedeni": neden
            })

    print()
    print("KALITE KONTROL")
    for neden in sorted(kalite_sayac):
        print("  ", neden, ":", kalite_sayac[neden])
    print("  Toplam aday       :", len(final_rows) + len(reddedilen_rows))
    print("  ONAYLI             :", len(final_rows))
    print("  REDDEDILEN         :", len(reddedilen_rows))
    print("  Red raporu         :", KALITE_RED_CSV)
    print()
    print("DURUM DAGILIMI")

    for durum in sorted(
        durum_sayac,
        key=lambda x:
            int(x)
            if x.isdigit()
            else 999
    ):

        print(
            "Durum",
            durum,
            ":",
            durum_sayac[durum]
        )

    print()
    print(
        "RAW benzersiz EventID :",
        len(maclar)
    )

    print(
        "Kalite onayli final   :",
        len(final_rows)
    )

    print(
        "Final CSV             :",
        FINAL_CSV
    )

    return True


# =========================================================
# ANA PROGRAM - GITHUB 08:00 GUNLUK SONUC
# =========================================================

simdi = datetime.now()
bugun_dt = simdi.date()
dun_dt = bugun_dt - timedelta(days=1)

print("=" * 75)
print("ORAN AI - GITHUB GUNLUK SONUC v1.0")
print("=" * 75)

print(
    "Kontrol zamani :",
    simdi.strftime("%d.%m.%Y %H:%M:%S")
)

print(
    "Hedef tarih    :",
    dun_dt.strftime("%d.%m.%Y")
)

# 08:00 gorevi yalnizca onceki gunu isler.
dun_ok = tarihi_isle(
    dun_dt,
    simdi
)

print()
print("=" * 75)
print("GENEL RAPOR")
print("=" * 75)

print(
    "Dun sonucu    :",
    "OK" if dun_ok else "HATA"
)

print(
    "Guvenli sonuc : OLUSTURULDU"
)

print("=" * 75)

