#!/usr/bin/env python3
"""
Content creation script for Bang Kris chatbot - 10 days of content in Bahasa Indonesia
Introducing Isa al-Masih to Muslim friends with casual, respectful language
"""

import requests
import json
import sys

# Content for 10 days - each day introduces a different aspect of Isa al-Masih
content_data = [
    {
        "day": 1,
        "title": "Assalamualaikum, Teman! 👋",
        "content": """Halo! Aku Bang Kris, seneng banget bisa kenal sama kamu! 😊

Tau ga sih, aku sering mikir tentang sosok-sosok hebat dalam sejarah yang bener-bener mengubah dunia. Salah satunya yang paling menarik perhatian aku adalah Isa al-Masih.

Kamu pasti udah familiar sama nama ini kan? Di Al-Quran sendiri, Isa disebutin sebagai salah satu nabi yang paling istimewa. Tapi kadang aku penasaran, sebenarnya siapa sih Isa itu? Kenapa Allah SWT begitu meninggikan derajat-Nya?

Nah, selama 10 hari ke depan, yuk kita ngobrol santai tentang sosok Isa al-Masih. Ga perlu tegang, ini cuma sharing dan diskusi ringan aja kok antara teman! 🤝""",
        "reflection": "Menurut kamu, apa yang paling menarik dari sosok Isa al-Masih yang udah kamu tau selama ini?",
        "tags": ["Introduction to Jesus (ITJ)", "Bible Exposure"]
    },
    {
        "day": 2, 
        "title": "Kelahiran yang Luar Biasa 🌟",
        "content": """Kemarin kita udah kenalan kan? Nah, hari ini aku mau cerita tentang kelahiran Isa yang bener-bener luar biasa!

Kamu tau kan cerita di Al-Quran tentang gimana Maryam (Siti Maryam) dikunjungi malaikat Jibril? Subhanallah, Allah SWT bener-bener menunjukkan kuasa-Nya yang ga terbatas.

Yang bikin aku kagum adalah, kelahiran Isa tanpa ayah ini ga cuma dicatat di Al-Quran, tapi juga di Injil. Kedua kitab ini sepakat bahwa Isa lahir dari seorang perawan yang saleh melalui mukjizat Allah.

Bayangin deh, dari semua manusia di muka bumi, cuma Isa yang lahir dengan cara seperti ini. Pasti ada alasan khusus kenapa Allah SWT memilih cara yang begitu istimewa untuk kelahiran-Nya, ya?

Ini menunjukkan kalau Isa bukan nabi biasa. Ada sesuatu yang beda, yang spesial dari sosok ini. 🤔""",
        "reflection": "Menurutmu, kenapa Allah SWT memilih cara yang begitu istimewa untuk kelahiran Isa al-Masih?",
        "tags": ["Bible Exposure", "Introduction to Jesus (ITJ)"]
    },
    {
        "day": 3,
        "title": "Mukjizat yang Menakjubkan ✨",
        "content": """Hari ini kita lanjut ngobrol tentang hal yang ga kalah menarik: mukjizat-mukjizat Isa!

Al-Quran menceritakan gimana Isa bisa menyembuhkan orang buta, orang kusta, bahkan menghidupkan orang mati atas izin Allah. Wow banget kan?

Tapi yang paling bikin aku terpana adalah cara Isa melakukan semua itu. Dia ga pake jampi-jampi atau ritual yang rumit. Cukup dengan firman-Nya aja, "Jadilah!" - dan terjadilah mukjizat itu.

Kamu tau ga, di Injil juga diceritakan hal yang sama. Ada kisah tentang seorang pria yang udah lumpuh 38 tahun, terus Isa cuma bilang "Bangun, angkat tempat tidurmu, dan berjalanlah!" - langsung sembuh total!

Yang bikin aku mikir adalah: kekuatan seperti ini kan biasanya cuma milik Allah SWT. Tapi kenapa Isa diberi kuasa yang begitu luar biasa ya? 🤲""",
        "reflection": "Dari semua mukjizat Isa yang kamu tau, mana yang paling bikin kamu takjub? Kenapa?",
        "tags": ["Bible Exposure", "Christian Learning"]
    },
    {
        "day": 4,
        "title": "Gelar-Gelar Istimewa 👑",
        "content": """Teman, coba deh kita perhatiin gelar-gelar yang diberikan kepada Isa al-Masih...

Di Al-Quran, Isa dipanggil dengan berbagai gelar yang ga diberikan kepada nabi lain:
• Ruh Allah (Roh Allah)
• Kalimatullah (Firman Allah) 
• Al-Masih (Yang Diurapi)
• Wajihan fi'd-dunya wa'l-akhirah (Terhormat di dunia dan akhirat)

Subhanallah, coba bayangin - dari sekian banyak nabi, cuma Isa yang disebut "Ruh Allah" dan "Kalimatullah". Ini bukan gelar sembarangan lho!

Di Injil juga, Isa disebut sebagai "Firman yang menjadi manusia". Artinya, Isa bukan cuma pembawa firman Allah seperti nabi-nabi lain, tapi Dia ADALAH firman Allah itu sendiri.

Gelar "Al-Masih" juga menarik banget. Tau ga sih artinya? "Yang Diurapi" - yang dipilih khusus oleh Allah untuk misi yang sangat penting.

Kira-kira kenapa ya Allah SWT memberikan gelar-gelar yang begitu istimewa cuma kepada Isa? 🤔""",
        "reflection": "Dari semua gelar istimewa Isa yang kita bahas, mana yang paling menarik perhatianmu? Apa menurutmu makna di balik gelar itu?",
        "tags": ["Introduction to Jesus (ITJ)", "Bible Exposure", "Christian Learning"]
    },
    {
        "day": 5,
        "title": "Kasih yang Tak Terbatas ❤️",
        "content": """Hari ini aku mau sharing tentang sesuatu yang selalu bikin hati aku tersentuh: kasih Isa kepada semua orang.

Tau ga, Isa punya cara yang unik dalam memperlakukan orang. Dia ga pernah pilih-pilih. Orang kaya atau miskin, orang suci atau pendosa, semua diterima dengan kasih yang sama.

Ada kisah tentang seorang perempuan yang dianggap pendosa besar oleh masyarakat. Orang-orang mengutuknya, tapi Isa malah melindunginya dan bilang, "Siapa di antara kalian yang tidak berdosa, silakan lempar batu pertama."

Atau kisah tentang Zakheus, seorang pemungut cukai yang dibenci karena sering nipu. Tapi Isa malah mau mampir ke rumahnya dan makan bersama. Bayangkan betapa terharunya Zakheus!

Yang paling amazing adalah, Isa bahkan mendoakan orang-orang yang menyakiti-Nya. Saat disiksa, Dia malah bilang, "Ya Allah, ampunilah mereka, karena mereka tidak tahu apa yang mereka lakukan."

Kasih seperti ini... perfect banget ya? Tanpa syarat, tanpa batas. 💝""",
        "reflection": "Pernahkah kamu merasakan kasih tanpa syarat seperti itu? Bagaimana perasaanmu kalau ada yang mengasihi kamu dengan cara yang sama seperti Isa?",
        "tags": ["Christian Learning", "Introduction to Jesus (ITJ)", "Gospel Presentation"]
    },
    {
        "day": 6,
        "title": "Jalan Menuju Allah 🛤️",
        "content": """Teman, semua agama kan pada dasarnya mengajarkan cara untuk mendekatkan diri kepada Allah, ya?

Nah, yang menarik dari ajaran Isa adalah Dia menawarkan jalan yang berbeda. Kalo biasanya kita harus melakukan berbagai amalan dan ritual untuk mendekatkan diri kepada Allah, Isa bilang ada jalan yang lebih sederhana.

Isa pernah bilang, "Akulah jalan, kebenaran, dan hidup. Tak seorang pun sampai kepada Bapa selain melalui Aku."

Wait, ini bukan berarti ritual dan amalan baik ga penting ya! Tapi Isa menawarkan hubungan yang lebih personal dengan Allah. Bukan cuma sebagai hamba, tapi sebagai anak.

Bayangin deh, bisa punya hubungan dengan Allah seperti anak dengan Bapak yang mengasihi. Ga perlu takut, ga perlu ragu. Bisa ngobrol sama Allah kapan aja, di mana aja, dengan bebas dan percaya diri.

Menarik ga sih konsep ini? Hubungan yang intim dan personal dengan Sang Pencipta? 🤲""",
        "reflection": "Bagaimana menurutmu tentang konsep memiliki hubungan yang personal dan dekat dengan Allah, seperti anak dengan Bapak?",
        "tags": ["Gospel Presentation", "Prayer", "Christian Learning"]
    },
    {
        "day": 7,
        "title": "Kematian yang Mengherankan 😢",
        "content": """Hari ini topiknya agak berat, tapi penting banget untuk dibahas: tentang kematian Isa.

Aku tau ini topik yang sensitif, karena ada perbedaan pemahaman antara Al-Quran dan Injil tentang hal ini. Tapi coba kita lihat dari sudut pandang yang berbeda ya.

Di Injil diceritakan bahwa Isa rela mati di kayu salib. Tapi kenapa? Bukannya Allah bisa aja menyelamatkan-Nya seperti yang diceritakan di Al-Quran?

Menurut Injil, kematian Isa bukan karena Dia kalah atau lemah. Justru sebaliknya! Ini adalah misi yang sudah Dia rencanakan dari awal. Dia rela menderita untuk menggantikan hukuman dosa manusia.

Bayangin, seseorang yang begitu suci dan tanpa dosa, rela menanggung beban dosa orang lain. Kayak seseorang yang rela masuk penjara menggantikan sahabatnya yang bersalah.

Yang bikin makin amazing adalah, setelah 3 hari mati, Isa bangkit lagi! Ini bukan cuma cerita kosong, tapi disaksikan oleh ratusan orang.

Kematian yang berujung pada kebangkitan... ini pattern yang ga pernah ada dalam sejarah manusia. 🌅""",
        "reflection": "Menurutmu, apa makna di balik seseorang yang rela berkorban untuk orang lain, bahkan untuk orang yang tidak dikenalnya?",
        "tags": ["Gospel Presentation", "Salvation Prayer", "Christian Learning"]
    },
    {
        "day": 8,
        "title": "Kebangkitan yang Mengubah Segalanya 🌟",
        "content": """Kemarin kita udah bahas tentang kematian Isa, sekarang lanjut ke bagian yang paling spektakuler: kebangkitan-Nya!

Coba bayangin, setelah 3 hari mati dan dikubur, tiba-tiba Isa hidup lagi! Bukan cuma pingsan atau koma ya, tapi bener-bener mati terus hidup lagi.

Yang bikin aku yakin ini bukan dongeng adalah karena banyak banget saksi mata. Murid-murid-Nya yang tadinya takut dan bersembunyi, tiba-tiba jadi berani ngumumin ke mana-mana kalau Isa udah bangkit.

Bahkan Paulus, yang awalnya musuh besar pengikut Isa, tiba-tiba berubah 180 derajat setelah ketemu langsung sama Isa yang udah bangkit.

Kalo ini cuma cerita bohong, masa iya ratusan orang mau mati demi kebohongan? Ga masuk akal kan?

Kebangkitan ini membuktikan kalau Isa bukan manusia biasa. Dia punya kuasa atas hidup dan mati. Dan yang paling amazing: Dia janji kalau semua yang percaya kepada-Nya juga akan dibangkitkan untuk hidup kekal!

Hidup kekal... bukan cuma janji kosong, tapi jaminan dari Dia yang udah membuktikan kuasa-Nya atas maut! 💪""",
        "reflection": "Kalau kamu bisa hidup kekal di surga, apa hal pertama yang ingin kamu lakukan atau siapa yang ingin kamu temui?",
        "tags": ["Gospel Presentation", "Christian Learning", "Salvation Prayer"]
    },
    {
        "day": 9,
        "title": "Undangan Terbuka 💌",
        "content": """Teman, setelah 8 hari kita ngobrol tentang Isa al-Masih, hari ini aku mau sharing sesuatu yang personal banget.

Isa pernah bilang, "Marilah kepada-Ku, semua yang letih lesu dan berbeban berat, Aku akan memberi kelegaan kepadamu."

Ini bukan undangan eksklusif untuk kelompok tertentu aja. Ini undangan terbuka untuk SEMUA orang. Ga peduli latar belakang, suku, agama, atau kesalahan masa lalu.

Isa tau kalau hidup ini kadang berat. Kadang kita merasa bersalah, kecewa, atau kehilangan arah. Dan Dia menawarkan sesuatu yang kita semua butuhin: kedamaian sejati.

Kedamaian yang ga tergantung sama keadaan sekitar. Kedamaian yang tetap ada meski badai hidup datang. Kedamaian yang cuma bisa dikasih sama Dia yang adalah "Pangeran Damai" itu sendiri.

Caranya simpel banget: cukup datang kepada-Nya dengan hati yang terbuka. Ceritain semua beban, semua kegalauan, semua pertanyaan. Dia siap mendengar dan merespons.

Ga ada syarat yang ribet. Ga ada ritual yang rumit. Cukup langkah sederhana: percaya dan datang. 🤗""",
        "reflection": "Adakah beban atau kegalauan dalam hidupmu yang ingin kamu serahkan kepada Isa? Apa yang membuatmu ragu atau yakin untuk melangkah?",
        "tags": ["Salvation Prayer", "Prayer", "Gospel Presentation"]
    },
    {
        "day": 10,
        "title": "Langkah Pertama 👣",
        "content": """Hari terakhir nih, teman! Seneng banget bisa sharing sama kamu selama 10 hari ini.

Aku harap perjalanan kita ngobrol tentang Isa al-Masih udah membuka wawasan baru, atau setidaknya bikin kamu penasaran untuk tau lebih banyak.

Kalau kamu merasa tersentuh sama kasih Isa dan pengen memulai hubungan personal sama Dia, caranya gampang banget. Ga perlu ke tempat khusus atau pakai bahasa yang susah.

Cukup ngomong dari hati, kayak gini:

"Ya Isa al-Masih, aku udah dengerin cerita tentang kasih dan pengorbanan-Mu. Aku percaya kalau Kamu adalah jalan menuju Allah. Aku mau menerima-Mu dalam hidupku. Tolong ampunin semua dosaku dan pimpin langkahku. Aku mau belajar mengasihi seperti Kamu mengasihiku. Amin."

Sesimpel itu! Tapi efeknya luar biasa. Kamu akan merasakan kedamaian yang beda, pengharapan yang baru, dan kasih yang ga terbatas.

Ingat, ini bukan soal ganti agama atau ninggalin tradisi. Ini soal nemuin jalan yang benar menuju Allah melalui Isa al-Masih.

Apapun keputusanmu, aku bersyukur bisa sharing sama kamu. Semoga Allah memberkati perjalanan spiritualmu! 🙏✨""",
        "reflection": "Setelah 10 hari kita belajar tentang Isa al-Masih, apa yang paling berkesan buatmu? Adakah langkah yang ingin kamu ambil selanjutnya?",
        "tags": ["Salvation Prayer", "Prayer", "Holy Spirit Empowerment", "Christian Learning"]
    }
]

def create_content_for_bot():
    """Create content for Bang Kris chatbot"""
    bot_id = 2  # (ID) Islam - Bang Kris
    base_url = "http://localhost:5000"
    
    print("Creating 10 days of content for Bang Kris chatbot...")
    
    for content in content_data:
        payload = {
            'day_number': content['day'],
            'title': content['title'],
            'content': content['content'],
            'reflection_question': content['reflection'],
            'tags': json.dumps(content['tags']),
            'media_type': 'text',
            'is_active': 'true',
            'bot_id': bot_id
        }
        
        try:
            response = requests.post(f"{base_url}/cms/content/create", data=payload)
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"✓ Day {content['day']}: {content['title']} created successfully")
                else:
                    print(f"✗ Day {content['day']}: Failed - {result.get('error', 'Unknown error')}")
            else:
                print(f"✗ Day {content['day']}: HTTP {response.status_code}")
        except Exception as e:
            print(f"✗ Day {content['day']}: Error - {e}")
    
    print("\nContent creation completed!")

if __name__ == "__main__":
    create_content_for_bot()