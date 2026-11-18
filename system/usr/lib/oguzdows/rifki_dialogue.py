"""Bütün rehber panellerinin ve hareket düğmelerinin Türkçe anlatımı."""
HELLO = 'Merhaba, ben Rıfkı. Kurulum, disk, açılış ve donanım adımlarında yanındayım. Bana yazabilir veya yardım düğmelerine basabilirsin. Artık bütün yardım yanıtlarımı seslendirebilirim. İstersen küçük kedi olarak pencere kenarına da gelirim.'
PANELS = {
    'welcome': 'OğuzDows rehberindesin. Denemek, kurmak veya donanımını tanımak için kartlardan birini seç. Kur düğmesi yalnızca canlı USB oturumunda çalışır. Donanım ve sürücüler ile duvar kâğıtları sekmelerine üstten geçebilirsin. Diskine yazılacak işlemleri kurucunun son özetinde sen onaylarsın.',
    'hardware': 'Donanım ve sürücüler paneli. Raporu yenileyebilir, kendi seçtiğin bir dosyaya kaydedebilir veya ağ bağlantılarını açabilirsin. Ek Broadcom ve eski Intel paketleri yalnızca eşleşen kartta, lisans ve yönetici onayıyla kurulur. Gri düğme eksik sistem değil, o pakete uygun kart bulunmadığı anlamına gelir. Rapor hiçbir yere gönderilmez.',
    'wallpapers': 'Duvar kâğıtları paneli. Altı çizim ve altı foto-gerçekçi manzara arasından birini seç. Yeni manzaralar yapay zekâ üretimidir. Küçük resme bastığında duvar kâğıdı uygulanır ve seçimin kaydedilir. Kalıcılıksız canlı USB oturumunda yeniden başlatma bu seçimi sıfırlar.',
    'settings': 'Rıfkı ayarları. Bütün panelleri anlat seçeneği sekme açıklamalarını otomatik okur. Rıfkı konuşsun sesi açar veya kapatır. Son mesajı oku ile tekrar dinleyebilir, sesi durdur ile hemen susturabilirsin. Küçük kediyi gizleyebilir, hareketi duraklatabilir veya otomatik oyunları kapatabilirsin. Bu tercihler kurulum ayarlarını değiştirmez.',
}
MOTIONS = {
    'perch': 'Pencere kenarında dinleniyorum. Beni tıklamak zorunda değilsin; kurulum düğmeleri kullanılabilir kalıyor.',
    'jump': 'Hop! Pencerenin üst kenarına zıplıyorum. Üstte yer yoksa kendi oyun alanımda kalırım; düğmelerin üstünü kapatmam.',
    'tail': 'Burada oturup kuyruğumu sallayayım. İstediğin zaman hareketi durdurabilirsin.',
    'feather': 'Bir tüy topu geldi! Patimle yakalayıp biraz oynayayım. Kurulumun ilerlemesi bu oyundan bağımsız.',
    'tea': 'Çay molası! Küçük demliğimi hazırlayıp çayı doldurayım, sonra bir yudum içeyim. Bu yalnızca eğlenceli bir animasyon; kurulum sürüyor.',
}
STAGES = {
    'preparing': ('Kurucu hazırlanıyor', 'Canlı sistem ve kurulum kaynağı kontrol ediliyor. Diskine henüz yazıldığını varsayma.'),
    'ready': ('Seçimlerini kontrol et', 'Dil, klavye, disk ve kullanıcı bilgilerini kurucuda seç. Son özeti sen onaylayacaksın.'),
    'partition': ('Disk işlemleri başladı', 'Onayladığın bölüm düzeni uygulanıyor. Bilgisayarı kapatma.'),
    'copying': ('Dosyalar yerleşiyor', 'Dosyalar kopyalanıyor. Yüzde ve gerçek ilerleme kurucu ekranında; tahminî bir ilerleme göstermiyorum.'),
    'bootloader': ('Disk açılışı hazırlanıyor', 'Önyükleyici ve başlangıç dosyaları hazırlanıyor. Bu adım bitmeden başarı bildirmeyeceğim.'),
    'complete': ('Kurulum tamamlandı', 'Bütün kurulum işleri tamamlandı. Sonuç ekranını incele; diskten ilk açılış ayrıca denenmelidir.'),
}
