from django.shortcuts import render


def landing_page(request):
    return render(request, "cultivation/landing.html")

def kelola_panduan(request):
    dummy_guides = [
        {
            "nama_tanaman": "Tomat",
            "cara_menanam": [
                "Lorem ipsum dolor sit amet consectetur",
                "Adipiscing elit sed do eiusmod tempor",
                "Incididunt ut labore et dolore magna",
            ],
            "media_tanam": "Lorem ipsum dolor",
            "kebutuhan_air": "Lorem ipsum dolor sit amet",
            "kebutuhan_cahaya": "Lorem ipsum",
            "pemupukan": "Lorem ipsum dolor sit amet",
            "waktu_panen": "Lorem ipsum dolor",
        },
        {
            "nama_tanaman": "Bayam",
            "cara_menanam": [
                "Ut enim ad minim veniam quis",
                "Nostrud exercitation ullamco laboris nisi",
                "Ut aliquip ex ea commodo consequat",
            ],
            "media_tanam": "Lorem ipsum dolor",
            "kebutuhan_air": "Lorem ipsum dolor sit amet",
            "kebutuhan_cahaya": "Lorem ipsum",
            "pemupukan": "Lorem ipsum dolor sit amet",
            "waktu_panen": "Lorem ipsum dolor",
        },
        {
            "nama_tanaman": "Cabai",
            "cara_menanam": [
                "Duis aute irure dolor in reprehenderit",
                "In voluptate velit esse cillum dolore",
                "Eu fugiat nulla pariatur excepteur sint",
            ],
            "media_tanam": "Lorem ipsum dolor",
            "kebutuhan_air": "Lorem ipsum dolor sit amet",
            "kebutuhan_cahaya": "Lorem ipsum",
            "pemupukan": "Lorem ipsum dolor sit amet",
            "waktu_panen": "Lorem ipsum dolor",
        },
    ]

    context = {
        "guides": dummy_guides,
    }
    return render(request, "cultivation/kelola_panduan.html", context)