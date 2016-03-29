'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
# coding=UTF-8
from pushkin.database import database

language_map = {
    "English": 11,
    "English UK": 1,
    "German": 2,
    "Italian": 3,
    "Spanish": 4,
    "Portuguese": 5,
    "French": 6,
    "Serbian": 7,
    "Greek": 56,
    "Polish": 97,
    "Romanian": 98,
    "Russian": 99,
    "Turkish": 118,
    "Japanese": 65,
    "Chinese": 35,
    "Taiwan": 1035,
    "Dutch": 89,
    "Czech": 41,
    "Thai": 138,
    "Swedish": 112,
    "Israeli": 63,
    "Malayan": 136,
    "South Korean": 109,
    "Finnish": 51,
    "Vietnamese": 129,
    "Brazilian": 25,
    "Indonesian": 132,
    "Norwegian": 93,
    "Danish": 42,
    "Arabic": 130,
}

translation = {
    "English": "You've been challenged to a friendly! Can you outplay the opponent?",
    "English UK": "You've been challenged to a friendly! Can you outplay the opponent?",
    "Arabic": "أمامك تحد في مباراة ودية! هل يمكنك التغلب على المنافس؟",
    "Chinese": "你接到了友谊赛邀请！你能打败对手吗？",
    "Taiwan": "你已成功挑戰好友！你有辦法超越對手嗎？",
    "Czech": "Byl jsi vyzván k přátelskému utkání! Přehraješ svého soupeře?",
    "Danish": "Du er blevet udfordret til en venskabskamp! Kan du udspille din modstander?",
    "Dutch": "Je bent uitgedaagd om een vriendschappelijke wedstrijd te spelen! Kun je de tegenstander verslaan?",
    "Finnish": "Sinut on haastettu ystävyysotteluun! Pystytkö voittamaan?",
    "French": "On te défie à l'occasion d'une rencontre amicale ! Seras-tu meilleur que ton adversaire ?",
    "German": "Du wurdest zu einem Freundschaftsspiel herausgefordert! Kannst du den Gegner besiegen?",
    "Greek": "Σας κάλεσαν σε φιλικό αγώνα! Μπορείτε να νικήσετε τον αντίπαλο;",
    "Israeli": "הוזמנת למשחק ידידות! האם תצליח לשחק טוב יותר מהיריב?",
    "Indonesian": "Kamu ditantang dalam pertandingan persahabatan! Bisa ungguli lawan?",
    "Italian": "Sei stato invitato a disputare un'amichevole. Riuscirai a battere il tuo avversario?",
    "Japanese": "親善試合の挑戦状が届いた！相手チームに勝てるかな？",
    "South Korean": "친선 경기 초대를 받았습니다! 상대를 꺾을 준비가 되셨나요?",
    "Malayan": "Anda telah dicabar untuk sebuah perlawanan persahabatan! Bolehkah anda mengalahkan pihak lawan?",
    "Norwegian": "Du er blitt utfordret til en vennskapskamp! Kan du vinne over motstanderen?",
    "Polish": "Zostałeś zaproszony do rozegrania meczu towarzyskiego! Pokonasz przeciwnika?",
    "Brazilian": "Você foi desafiado para um amistoso! Consegue superar o adversário?",
    "Portuguese": "Foste desafiado para um jogo amigável! Consegues jogar melhor do que o adversário?",
    "Romanian": "Ai fost provocat la un meci amical! Poți juca mai bine decât adversarul?",
    "Russian": "Тебе вызвали на товарищеский матч! Сможешь победить?",
    "Serbian": "Pozvan si na prijateljsku utakmicu! Možeš li da nadigraš protivnika?",
    "Spanish": "¡Has sido retado a un amistoso! ¿Podrás derrotar a tu rival?",
    "Swedish": "Du har utmats till en vänskapsmatch! Kan du spela ut motståndaren?",
    "Thai": "คุณได้รับคำเชิญให้เล่นแมทช์กระชับมิตร! คุณจะสามารถเอาชนะคู่แข่งได้หรือไม่",
    "Turkish": "Dostluk maçına çağrıldın! Rakibini alt edebilir misin?",
    "Vietnamese": "Bạn đã được mời đá giao hữu! Bạn có thể đánh bại đối thủ không?",
}
if len(set(translation.keys()) - set(language_map.keys())) == 0:
    for lang, msg in translation.items():
        database.add_message(message_name='friendly_scheduled', language_id=language_map[lang],
                             message_title='Top Eleven 2016',
                             message_text=msg, trigger_event_id=100000, cooldown_ts=60 * 60 * 1000,
                             screen='LiveMatchScene')
else:
    print("ERROR: some languages are missing in language_map")
