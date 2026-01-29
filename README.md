# centering_test

## Amaç
Türkçe bağımlılık çözümlemede UAS/LAS ölçmek ve **Centering Theory** temelli yeniden sıralama (reranking) ile sonuçları iyileştirme fikrini denemek.

## Yöntem
1. **Akademik standart veri** olarak UD Turkish IMST test seti kullanıldı.
2. **Temel ayrıştırıcı**: Stanza (tokenize+pos+depparse).
3. **Karşılaştırmalı ayrıştırıcı**: UDPipe (spaCy-UDPipe ile).
4. **Centering tabanlı rerank**: İki ayrıştırıcının çıktıları, her cümle için centering geçiş skoruyla karşılaştırıldı ve daha yüksek skor seçildi.
5. UAS/LAS, seçilen parse’lar ile altın ağaçlara karşı hesaplandı.

## Merkezleme Kuramını Nasıl Kullandık?
- Her cümle için ayrıştırıcı çıktısından **forward centers (Cf)** çıkarıldı: isimler/özel isimler/ zamirler, bağımlılık ilişkilerine göre ağırlıklandırıldı (özne > nesne > diğerleri).
- Bir önceki cümlenin Cf listesiyle karşılaştırarak **backward center (Cb)** ve **preferred center (Cp)** belirlendi.
- İki cümle arasındaki geçiş tipi (Continue/Retain/Smooth-Shift/Rough-Shift) çıkarıldı ve **skorlandı**.
- Aynı cümle için Stanza ve UDPipe parse’ları bu centering skoruyla karşılaştırıldı; **daha yüksek skorlu parse** seçilerek UAS/LAS hesaplandı.
### POS Tagging Belirsizliğini Azaltma
Merkezleme kuramı, POS etiketlerini **söylemsel tutarlılıkla** sınayarak yapısal belirsizlikleri azaltır:
- İki parser'dan gelen POS etiketleri, söylemsel merkezleri (Cf) farklı şekilde belirler.
- Her iki POS seçeneği için centering geçiş skoru hesaplanır.
- **Daha tutarlı söylemsel yapı** üreten (yüksek centering skoru) POS etiketleri seçilir.
- Sonuç: Söylemsel olarak daha uyumlu POS etiketlemesi.
## Sonuçlar (UD Turkish IMST test)

### Dependency Parsing (UAS/LAS)
- **Stanza**: UAS 92.65 / LAS 89.19
- **UDPipe**: UAS 77.53 / LAS 57.90
- **Centering rerank**: UAS 92.59 / LAS 89.02

> Not: Bu koşulda rerank, Stanza'yı geçemedi. Geliştirme setinde centering ağırlıklarını optimize etmek ve daha güçlü ikinci parser eklemek muhtemel iyileştirme yollarıdır.

### POS Tagging (Belirsizlik Azaltma)
- **Stanza**: POS Accuracy 98.43%
- **UDPipe**: POS Accuracy 94.46%
- **Centering rerank**: POS Accuracy 98.43%

> Merkezleme kuramı, iki parser'ın POS etiketlerini söylemsel tutarlılıkla sınayarak en iyi seçimi yapıyor. Stanza'nın POS performansı zaten çok yüksek olduğundan rerank aynı seviyeyi korudu.

## Çalıştırma
- Tek ayrıştırıcı değerlendirmesi: [evaluate_ud_tr.py](evaluate_ud_tr.py)
- Dependency parsing rerank: [evaluate_ud_tr_rerank.py](evaluate_ud_tr_rerank.py)
- POS tagging rerank (belirsizlik azaltma): [evaluate_pos_centering.py](evaluate_pos_centering.py)

Her script, UD Turkish IMST test setini otomatik indirir ve sonuçları konsola yazar.

## Üretilen Dosyalar
- [evaluate_ud_tr.py](evaluate_ud_tr.py): Stanza ile temel UAS/LAS değerlendirmesi.
- [evaluate_ud_tr_rerank.py](evaluate_ud_tr_rerank.py): Stanza + UDPipe + centering tabanlı dependency rerank.
- [evaluate_pos_centering.py](evaluate_pos_centering.py): Centering ile POS belirsizlik azaltma (rerank).
- [tr_pos_test.py](tr_pos_test.py): Örnek Türkçe POS etiketleme testi.