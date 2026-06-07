# Correo electr\xf3nico del administrador al que llegaran las notificaciones de ISPs caidos
:global foCorreoAdministrador "alarmassentinela@gmail.com";

# Bandera que indica si se van a enviar correos de notificacion "si"/"no"
:global foEnvioEmailsNotificacion "si";

# IP de DNS a donde se lanzan las pruebas de ping
# En este caso se usa una IP de OpenDNS
:global foIpDNS  "208.67.222.222";

# Cantidad de pruebas ping a realizar para determinar si un ISP est\xe1 caido
:global foNPruebasPing 5;

# Definici\xf3n de ISPs y capacidades proporcionales
:global foIsps {{1;1};{2;2};{3;1};{5;1};{6;1} };

# Relacion de ISPs con Interfaces
:global foRelIspInterfaz {{1;"ether1_WAN"};{2;"ether2_WAN"};{3;"ether3_WAN"};{4;"ether4_WAN"};{5;"ether5_WAN"};{6;"ether6_WAN"};};

