# -*- coding: utf-8 -*-

import requests
import csv
import os
import re
from datetime import datetime, timedelta

URL = "https://arsiv.mackolik.com/AjaxHandlers/ProgramDataHandler.ashx"

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

MASTER = "collector_canli_master.csv"
PREMATCH = "collector_canli_prematch.csv"
SNAPSHOT = "collector_canli_snapshots.csv"

MASTER_FIELDS = [
    "Tarih", "Saat", "EventID", "Ev", "Deplasman",
    "Ilk_Gorulme_Zamani",
    "Ilk_MS1", "Ilk_MSX", "Ilk_MS2",
    "Ilk_KG_Var", "Ilk_KG_Yok",
    "Ilk_15_Alt", "Ilk_15_Ust",
    "Ilk_25_Alt", "Ilk_25_Ust",
    "Ilk_35_Alt", "Ilk_35_Ust",
    "Son_Gorulme_Zamani",
    "Son_Durum"
]

PREMATCH_FIELDS = [
    "Tarih", "Saat", "EventID", "Ev", "Deplasman",
    "Son_PreMatch_Zamani",
    "MS1", "MSX", "MS2",
    "KG_Var", "KG_Yok",
    "ALT_15", "UST_15",
    "ALT_25", "UST_25",
    "ALT_35", "UST_35",
    "Durum"
]

SNAPSHOT_FIELDS = [
    "Kayit_Zamani",
    "Tarih", "Saat", "EventID", "Ev", "Deplasman",
    "MS1", "MSX", "MS2",
    "KG_Var", "KG_Yok",
    "ALT_15", "UST_15",
    "ALT_25", "UST_25",
    "ALT_35", "UST_35",
    "Mac_Durum"
]


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
            fields.append("".join(current).strip())
            current = []

        else:
            current.append(ch)

    fields.append("".join(current).strip())

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
            sonuc.append(text[start:i + 1])

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

        if not re.match(r"^\[\s*\d+\s*,", arr):
            continue

        fields = alanlara_ayir(arr)

        if len(fields) <= 50:
            continue

        if temizle(fields[7]) != hedef_tarih:
            continue

        event_id = temizle(fields[50])

        if not event_id:
            continue

        sonuc[event_id] = fields

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

    return tum, len(A), len(B)


def csv_dict_oku(dosya):

    sonuc = {}

    if not os.path.exists(dosya):
        return sonuc

    with open(
        dosya,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(
            f,
            delimiter=";"
        )

        for row in reader:

            eid = str(
                row.get("EventID", "")
            ).strip()

            if eid:
                sonuc[eid] = row

    return sonuc


def csv_dict_yaz(
    dosya,
    rows,
    fields
):

    gecici = dosya + ".tmp"

    with open(
        gecici,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            delimiter=";"
        )

        writer.writeheader()

        sirali = sorted(
            rows.values(),
            key=lambda x: (
                x.get("Tarih", ""),
                x.get("Saat", ""),
                x.get("EventID", "")
            )
        )

        for row in sirali:

            writer.writerow({
                alan: row.get(alan, "")
                for alan in fields
            })

    os.replace(
        gecici,
        dosya
    )


def snapshot_ekle(
    kayit_zamani,
    fields,
    eid
):

    dosya_var = os.path.exists(
        SNAPSHOT
    )

    row = {
        "Kayit_Zamani": kayit_zamani,
        "Tarih": temizle(fields[7]),
        "Saat": temizle(fields[6]),
        "EventID": eid,
        "Ev": temizle(fields[1]),
        "Deplasman": temizle(fields[3]),

        "MS1": oran(fields[16]),
        "MSX": oran(fields[17]),
        "MS2": oran(fields[18]),

        "KG_Var": oran(fields[39]),
        "KG_Yok": oran(fields[40]),

        "ALT_15": oran(fields[44]),
        "UST_15": oran(fields[45]),

        "ALT_25": oran(fields[22]),
        "UST_25": oran(fields[23]),

        "ALT_35": oran(fields[46]),
        "UST_35": oran(fields[47]),

        "Mac_Durum": temizle(fields[5])
    }

    with open(
        SNAPSHOT,
        "a",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=SNAPSHOT_FIELDS,
            delimiter=";"
        )

        if not dosya_var:
            writer.writeheader()

        writer.writerow(row)


def mac_basladi_mi(tarih, saat):

    try:

        baslama = datetime.strptime(
            tarih + " " + saat,
            "%d.%m.%Y %H:%M"
        )

        return datetime.now() >= baslama

    except:
        return True


def master_yeni_satir(
    fields,
    eid,
    zaman
):

    return {
        "Tarih": temizle(fields[7]),
        "Saat": temizle(fields[6]),
        "EventID": eid,
        "Ev": temizle(fields[1]),
        "Deplasman": temizle(fields[3]),

        "Ilk_Gorulme_Zamani": zaman,

        "Ilk_MS1": oran(fields[16]),
        "Ilk_MSX": oran(fields[17]),
        "Ilk_MS2": oran(fields[18]),

        "Ilk_KG_Var": oran(fields[39]),
        "Ilk_KG_Yok": oran(fields[40]),

        "Ilk_15_Alt": oran(fields[44]),
        "Ilk_15_Ust": oran(fields[45]),

        "Ilk_25_Alt": oran(fields[22]),
        "Ilk_25_Ust": oran(fields[23]),

        "Ilk_35_Alt": oran(fields[46]),
        "Ilk_35_Ust": oran(fields[47]),

        "Son_Gorulme_Zamani": zaman,
        "Son_Durum": "PREMATCH"
    }


def prematch_satir(
    fields,
    eid,
    zaman,
    durum="PREMATCH"
):

    return {
        "Tarih": temizle(fields[7]),
        "Saat": temizle(fields[6]),
        "EventID": eid,
        "Ev": temizle(fields[1]),
        "Deplasman": temizle(fields[3]),

        "Son_PreMatch_Zamani": zaman,

        "MS1": oran(fields[16]),
        "MSX": oran(fields[17]),
        "MS2": oran(fields[18]),

        "KG_Var": oran(fields[39]),
        "KG_Yok": oran(fields[40]),

        "ALT_15": oran(fields[44]),
        "UST_15": oran(fields[45]),

        "ALT_25": oran(fields[22]),
        "UST_25": oran(fields[23]),

        "ALT_35": oran(fields[46]),
        "UST_35": oran(fields[47]),

        "Durum": durum
    }


print("=" * 75)
print("ORAN AI - CANLI COLLECTOR v1.1")
print("ILK ORAN + SNAPSHOT + SON PREMATCH")
print("=" * 75)

simdi = datetime.now()

bugun_dt = simdi.date()
yarin_dt = bugun_dt + timedelta(days=1)

print(
    "Kontrol zamani :",
    simdi.strftime("%d.%m.%Y %H:%M:%S")
)

print(
    "Bugun          :",
    bugun_dt.strftime("%d.%m.%Y")
)

print(
    "Yarin          :",
    yarin_dt.strftime("%d.%m.%Y")
)

master = csv_dict_oku(
    MASTER
)

prematch = csv_dict_oku(
    PREMATCH
)

master_once = len(master)

toplam_gorulen = 0
yeni_sayi = 0
prematch_guncellenen = 0
kilitlenen = 0
baslamis_yeni_atlandi = 0

yeni_maclar = []

for tarih_dt in [
    bugun_dt,
    yarin_dt
]:

    hedef = tarih_dt.strftime(
        "%d.%m.%Y"
    )

    print()
    print("-" * 75)
    print("TARIH:", hedef)

    try:

        maclar, a_sayi, b_sayi = (
            gunu_cek(tarih_dt)
        )

    except Exception as e:

        print(
            "CEKIM HATASI:",
            e
        )

        continue

    print(
        "A kaynagi       :",
        a_sayi
    )

    print(
        "B kaynagi       :",
        b_sayi
    )

    print(
        "Benzersiz toplam:",
        len(maclar)
    )

    toplam_gorulen += len(maclar)

    su_an_ids = set(maclar)

    for eid, fields in maclar.items():

        tarih = temizle(
            fields[7]
        )

        saat = temizle(
            fields[6]
        )

        zaman = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        basladi = mac_basladi_mi(
            tarih,
            saat
        )

        # Her gorulen durum snapshot'a yazilir.
        snapshot_ekle(
            zaman,
            fields,
            eid
        )

        # ---------------------------------
        # ILK KEZ GORULEN
        # ---------------------------------

        if eid not in master:

            if basladi:

                baslamis_yeni_atlandi += 1
                continue

            master[eid] = master_yeni_satir(
                fields,
                eid,
                zaman
            )

            yeni_sayi += 1

            yeni_maclar.append(
                (
                    tarih,
                    saat,
                    eid,
                    temizle(fields[1]),
                    temizle(fields[3])
                )
            )

        else:

            master[eid][
                "Son_Gorulme_Zamani"
            ] = zaman

            if basladi:
                master[eid][
                    "Son_Durum"
                ] = "BASLADI"
            else:
                master[eid][
                    "Son_Durum"
                ] = "PREMATCH"

        # ---------------------------------
        # SON PREMATCH
        # ---------------------------------

        if not basladi:

            prematch[eid] = prematch_satir(
                fields,
                eid,
                zaman,
                "PREMATCH"
            )

            prematch_guncellenen += 1

        else:

            # Daha once prematch yakalandiysa
            # oranlari ASLA degistirme.
            if eid in prematch:

                if (
                    prematch[eid].get(
                        "Durum"
                    ) != "KILITLI"
                ):

                    prematch[eid][
                        "Durum"
                    ] = "KILITLI"

                    kilitlenen += 1

    # ---------------------------------
    # LISTEDEN CIKANLAR
    # ---------------------------------

    for eid, row in master.items():

        if row.get(
            "Tarih"
        ) != hedef:
            continue

        if eid in su_an_ids:
            continue

        if row.get(
            "Son_Durum"
        ) != "BASLADI":

            row[
                "Son_Durum"
            ] = "LISTEDE_YOK"

        if eid in prematch:

            if (
                prematch[eid].get(
                    "Durum"
                ) == "PREMATCH"
            ):

                prematch[eid][
                    "Durum"
                ] = "LISTEDE_YOK"


# ---------------------------------
# GECMIS PREMATCH KAYITLARINI KILITLE
# ---------------------------------

for eid, row in prematch.items():

    tarih = row.get(
        "Tarih",
        ""
    )

    saat = row.get(
        "Saat",
        ""
    )

    if (
        row.get("Durum") == "PREMATCH"
        and mac_basladi_mi(
            tarih,
            saat
        )
    ):

        row["Durum"] = "KILITLI"
        kilitlenen += 1


csv_dict_yaz(
    MASTER,
    master,
    MASTER_FIELDS
)

csv_dict_yaz(
    PREMATCH,
    prematch,
    PREMATCH_FIELDS
)


print()
print("=" * 75)
print("CANLI COLLECTOR v1.1 RAPORU")
print("=" * 75)

print(
    "Master once             :",
    master_once
)

print(
    "Bu tur gorulen          :",
    toplam_gorulen
)

print(
    "Yeni PREMATCH EventID   :",
    yeni_sayi
)

print(
    "Baslamis yeni atlandi   :",
    baslamis_yeni_atlandi
)

print(
    "Son PREMATCH guncellendi:",
    prematch_guncellenen
)

print(
    "Bu tur kilitlenen       :",
    kilitlenen
)

print(
    "Master toplam           :",
    len(master)
)

print(
    "Prematch toplam         :",
    len(prematch)
)

print(
    "Ana database            : DEGISTIRILMEDI"
)

print(
    "Canli master            :",
    MASTER
)

print(
    "Son prematch            :",
    PREMATCH
)

print(
    "Snapshot                :",
    SNAPSHOT
)


if yeni_maclar:

    print()
    print("=" * 75)
    print("ILK KEZ PREMATCH YAKALANANLAR")
    print("=" * 75)

    for (
        tarih,
        saat,
        eid,
        ev,
        dep
    ) in sorted(yeni_maclar):

        print(
            tarih,
            saat,
            "|",
            eid,
            "|",
            ev,
            "-",
            dep
        )


print()
print("=" * 75)
print("COLLECTOR v1.1 TAMAMLANDI")
print("=" * 75)