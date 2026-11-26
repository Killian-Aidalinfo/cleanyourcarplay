# cleanyourcarplay — document de conception

Date : 2026-11-26
Dépôt cible : `Killian-Aidalinfo/cleanyourcarplay` (public, MIT)
Statut : conception, aucun code écrit

---

## 1. Intention et pourquoi

Killian possède **plusieurs boîtiers CarPlay chinois sous Android** (familles AI Box
type Carlinkit TBox/Ultra, Ottocast Play2Video et clones). Il s'en sert comme
**simples adaptateurs CarPlay sans fil** : il ne lance jamais d'application Android
dessus, il démarre la voiture et veut CarPlay. La plupart sont alimentés par
l'allume-cigare ou un port USB du véhicule.

Symptôme déclencheur, dans ses mots : « des fois le CarPlay crash / l'appareil
reboot ».

Il veut un toolkit public, dans l'esprit de
[cleanyourtv](https://github.com/Gathin23/cleanyourtv), qui fasse **deux choses** :

1. **Diagnostiquer** — dire *pourquoi* le boîtier a planté ou redémarré.
2. **Nettoyer / transformer** — désactiver tout ce qui ne sert pas au métier
   d'adaptateur, pour gagner en RAM, en chauffe, en temps de démarrage et en
   stabilité.

Le diag passe en premier dans l'ordre d'exécution parce qu'une partie des reboots
constatés n'a **aucune cause logicielle** : les ports USB de véhicule et les prises
allume-cigare délivrent souvent moins de 1 A, et la tension s'effondre au
démarrage du moteur. Aucun `pm disable-user` ne corrige ça. Un outil qui
nettoierait sans mesurer laisserait croire au problème résolu.

### Exigence d'expérience, posée explicitement par Killian

> « moi perso j'avais juste donné l'url et claude avait déroulé le setup trql »

Le point d'entrée du produit est **une URL collée dans Claude Code**. L'utilisateur
ne lit pas de README et ne tape pas de commandes : un agent lit `PROMPT.md`, se
connecte au boîtier, pose quelques questions au bon moment et déroule. Les scripts
du dépôt sont les outils de l'agent, pas l'interface de l'utilisateur.

---

## 2. Ce qui diffère de cleanyourtv (et pourquoi ce n'est pas un fork)

| | cleanyourtv | cleanyourcarplay |
|---|---|---|
| Launcher | moitié du projet (app Java, ~572 Ko) | **hors périmètre** — l'UI Android n'est jamais regardée |
| Diag | absent | **moitié du produit** |
| Agressivité du nettoyage | limitée : la TV doit rester utilisable | forte : un seul métier à préserver |
| Garde-fou | un seul (HOME) | **pile de mirroring + APEX + réseau** |
| Sanction d'une erreur | réactiver depuis les Réglages | démontage, mode EDL, parfois brique |
| Cause de panne dominante | logicielle | **souvent électrique, hors logiciel** |

### La sanction d'erreur, en détail

C'est le point qui commande toute l'architecture. Le boîtier **n'a pas d'écran à
lui** : il s'affiche dans la fenêtre CarPlay de la voiture. Il n'a ni télécommande,
ni bouton reset accessible, ni menu Réglages atteignable. **Le seul canal de
retour en arrière est ADB par le Wi-Fi.** Donc toute modification qui empêche le
démarrage, ou simplement qui empêche le Wi-Fi de monter, détruit le canal qui
aurait permis de l'annuler.

Deux cas documentés sur le Carlinkit TBox Ultra 2 (X21-SC162, Snapdragon 690,
Android 15), source : [teab0www/carlinkit-tbox-ultra2-recovery](https://github.com/teab0www/carlinkit-tbox-ultra2-recovery) :

- **Perte du tactile sans panne visible.** `com.carsyso.main` héberge le service
  d'accessibilité qui réinjecte le tactile de l'écran du véhicule vers CarPlay.
  Désactivé, le boîtier démarre, l'image s'affiche, et l'écran ne répond plus au
  doigt. Rien ne « plante ». L'utilisateur n'a plus aucun moyen d'agir.
- **Bootloop sans issue logicielle.** Les applications empaquetées en APEX sous
  Android 13+ (`com.android.adservices.api`, `com.android.sdksandbox`,
  `com.android.federatedcompute.services`,
  `com.android.ondevicepersonalization.services`) désactivées donnent : boucle de
  démarrage, LED clignotante, pas de Wi-Fi, pas d'ADB. Seule sortie documentée :
  mode EDL Qualcomm (9008), bouton maintenu pendant le branchement USB, loader
  firehose tiers.

Troisième piège, du même dépôt : après un `pm disable-user`, il faut
`adb shell sync` et attendre avant de redémarrer, sinon les modifications sont
perdues au reboot — un lot entier a disparu ainsi.

**Conséquence de conception : le classement « sûr / risqué / jamais » n'est pas une
annexe du projet, c'est ce que le projet vend.**

---

## 3. Objectifs

1. Sur un boîtier **inconnu**, produire un profil exploitable sans connaissance
   préalable du modèle.
2. Répondre à « pourquoi ça a planté » en distinguant au minimum : coupure
   d'alimentation, surchauffe, tueur de mémoire, crash applicatif, panique noyau.
3. Désactiver le superflu **sans jamais perdre le tactile ni la capacité de
   redémarrer et de rejoindre le réseau**.
4. Tout annuler avec une commande.
5. Documenter la récupération par modèle, de la remise à zéro simple à l'EDL.
6. Point d'entrée : une URL collée dans Claude Code.
7. Accumuler les profils par modèle dans le dépôt, contribuables par des tiers.

## 4. Non-objectifs

- **Aucun launcher.** Pas une ligne de Java.
- Pas de root, pas de flash de firmware, pas de modification de `/system`.
- Pas de firmware ni de loader redistribué dans le dépôt.
- **Les dongles CarPlay sous Linux embarqué** (Carlinkit 3.0/4.0, CPC200-CCPA,
  Ottocast U2-X…) sont hors périmètre v1. Ils n'ont ni ADB ni paquets : c'est un
  autre métier, donc un autre projet. Le toolkit doit savoir les **reconnaître et
  le dire franchement**, pas les traiter.
- Pas de rétro-ingénierie des protocoles CarPlay / Android Auto (voir `catplay`,
  `ludwig-v/wireless-carplay-dongle-reverse-engineering` pour ça).
- Pas de démon embarqué en v1 (voir §7).

## 5. Anti-objectifs — ce qui rend le projet raté même s'il « fonctionne »

- Un boîtier qui démarre mais dont **l'écran ne répond plus au doigt**.
- Un boîtier **injoignable** : bootloop, ou Wi-Fi qui ne monte plus.
- Un outil qui laisse croire qu'il corrigera des reboots dont la cause est
  l'alimentation du véhicule.
- Des listes de paquets **recopiées d'un modèle à l'autre** sans vérification.
- Un nettoyage qui casse l'Android Auto d'un foyer qui en a besoin parce que
  l'outil a supposé « CarPlay uniquement ».

## 6. Contraintes

- **Aucun matériel disponible au moment de la conception**, un boîtier attendu à
  partir du 2026-11-27. Tout ce qui touche aux noms de propriétés, aux chemins
  système et aux paquets est à confirmer sur le premier boîtier réel. Le document le
  signale à chaque fois.
- **Aucun boîtier n'est sacrifiable.** C'est la contrainte la plus structurante du
  projet : il n'existe pas de matériel sur lequel on puisse se permettre de tenter
  une désactivation pour voir. Conséquences en §7.10 et §12.
- Les vérifications en voiture sont faites par Killian lui-même (hypothèse de
  l'auteur du document, à confirmer).
- Plusieurs modèles, de fabricants différents, inconnus a priori.
- Le boîtier est **aveugle au bureau** (pas d'écran hors voiture).
- Sur beaucoup de ces appareils, **l'ADB est ouvert sur le port 5555 à chaque
  démarrage, quoi que disent les réglages, et tourne en root** : n'importe qui sur
  le même Wi-Fi contrôle l'appareil. Source :
  [hamza39460/headunit-debloat-skill](https://github.com/hamza39460/headunit-debloat-skill).
- Android 13+ impose la contrainte APEX décrite en §2.

---

## 7. Architecture décidée

### 7.1 Atteindre un boîtier sans écran

Trois chemins, par ordre de préférence :

1. **USB, si l'appareil expose l'ADB sur son port USB-C** — à vérifier par le probe
   sur chaque modèle. C'est le meilleur chemin : un câble survit à un Wi-Fi qui ne
   remonte plus, c'est-à-dire exactement le pire scénario du §5. S'il existe, les
   lots passent par le câble et le Wi-Fi devient le chemin de secours au lieu
   d'être le seul.
2. **Le boîtier est sur le Wi-Fi de la maison** — c'est le **défaut documenté**.
   L'agent le trouve par ARP / mDNS, ou demande l'IP en dernier recours. Premier
   geste d'installation : faire rejoindre le Wi-Fi domestique au boîtier, une fois,
   depuis la voiture ou par USB.
3. **Le PC rejoint le point d'accès du boîtier** (SSID souvent de forme
   `AutoKit-xxxx`) — **fallback uniquement**, documenté dans `docs/`. Attention :
   ce point d'accès sert à l'appairage du téléphone et **ne fournit probablement
   aucun accès Internet** ; un agent qui s'y connecte avec l'unique interface du PC
   se coupe lui-même. Ce chemin suppose une seconde interface réseau (dongle Wi-Fi,
   partage de connexion).

> À confirmer sur matériel : la présence d'un ADB USB, et le comportement du point
> d'accès vis-à-vis d'Internet.

Conséquence : `screencap` et `input tap` / `input keyevent` sont les **seuls yeux et
les seules mains** de l'agent. Ce qui est un confort chez cleanyourtv devient ici
l'outil principal, et doit être fiable dès la première ligne de code.

### 7.2 Le probe, et le refus poli

Premier geste, avant toute modification. Il :

- établit la famille de l'appareil (**Android/ADB** vs **Linux/page web**) et
  **s'arrête proprement** si ce n'est pas un Android, en expliquant pourquoi et où
  aller ;
- relève modèle, fabricant, version d'Android, build, SoC, RAM, stockage ;
- liste les paquets et les classe (§7.4) ;
- établit si l'appareil expose l'**ADB sur USB** (voir §7.1) ;
- identifie la **pile de mirroring** : quel paquet fournit le service
  d'accessibilité qui injecte le tactile, quel paquet gère l'USB, l'audio,
  l'affichage ;
- écrit un **profil** sous `profiles/<fabricant>-<modèle>/`.

Le profil est à la fois la sauvegarde de l'état initial et la contribution
réutilisable par la communauté. Il est **anonymisé** : ni IP, ni SSID, ni numéro de
série, ni identifiant Android, ni adresse MAC.

### 7.3 Le diag, sans rien laisser tourner

Décision : **pas de démon embarqué en v1.** Android conserve déjà les preuves à
travers le redémarrage, ce qui suffit à répondre après coup à un plantage survenu
en roulant, sans PC à bord. L'agent lit :

- la **cause du dernier démarrage** (propriétés de type `ro.boot.bootreason` /
  `sys.boot.reason`) — c'est le discriminant principal entre coupure
  d'alimentation et défaillance logicielle sur plateforme Qualcomm ;
- la **boîte à lettres des crashs** (`dumpsys dropbox`) : crashs applicatifs,
  redémarrages système, paniques ;
- le **journal de panique persistant** (`/sys/fs/pstore/`) s'il existe ;
- la **température** (`/sys/class/thermal/`) et l'**alimentation**
  (`/sys/class/power_supply/`), en direct et sous charge ;
- un `bugreport` complet, **conservé en local et exclu du dépôt** (`.gitignore`) :
  il contient IP, SSID, numéro de série, adresse MAC, noms des téléphones appairés,
  historique Bluetooth et souvent la position. Seuls les **faits dérivés** (cause du
  boot, compteurs de crash, températures) entrent dans le profil versionné.

Le rapport rendu à l'utilisateur doit **conclure**, pas lister. Mais il conclut à la
hauteur de ce qu'il a mesuré : sans instrument, le toolkit **infère** la piste
électrique de la cause de boot et des compteurs d'alimentation, il ne la prouve pas.
La formule attendue est donc « trois redémarrages, tous avec des **signes de coupure
d'alimentation** ; commence par changer de source avant de nettoyer », et non « c'est
l'alimentation ». La mesure réelle (wattmètre USB, alimentation de laboratoire pour
simuler la chute de tension au démarrage) est décrite comme **étape manuelle
optionnelle** dans `references/power-test.md`.

> À confirmer sur matériel : les noms exacts des propriétés et la disponibilité de
> pstore varient selon le SoC et le fabricant. Le code doit dégrader proprement si
> une source manque, jamais échouer.

### 7.4 La classification — le cœur

Trois niveaux, écrits dans `references/classify.md`, appliqués par l'agent :

**JAMAIS** (l'agent refuse, même si l'utilisateur insiste, et explique) :
- la pile de mirroring complète : service d'accessibilité qui injecte le tactile,
  affichage, audio, USB, et le launcher système dont elle dépend ;
- les paquets APEX sous Android 13+ ;
- Wi-Fi, Bluetooth, réseau, `systemui`, `shell`, `settings`, les fournisseurs
  système essentiels ;
- tout ce qui porte le nom du fabricant du boîtier sans que son rôle soit établi.

**RISQUÉ** (désactivable seulement après question explicite, avec la conséquence
annoncée) :
- la pile Android Auto si l'utilisateur ne s'en sert pas — **mais la question est
  obligatoire** : Killian l'a souligné, ça dépend des téléphones du foyer ;
- l'audio et les appels Bluetooth s'ils transitent par le boîtier ;
- le service de mise à jour du firmware ;
- l'assistant vocal ;
- **`com.google.android.gms` et `com.google.android.gsf`**. Sur certains firmwares
  Android 13+, les couper casse des parcours d'appairage Bluetooth et la synthèse
  vocale utilisée par la navigation. Conséquence à annoncer avant de demander.

**SÛR** (désactivé sans demander) :
- Play Store, apps Google (Gmail, YouTube, Chrome, Maps…), boutique du fabricant,
  navigateur, lecteurs multimédias, explorateur de fichiers, télémétrie, fonds
  d'écran animés, démos, apps d'usine jamais lancées.

> Un adaptateur pur n'a besoin ni de boutique, ni de navigateur, ni de lecteur : la
> liste SÛR est bien plus large que sur une TV.

Règle transverse : **l'agent ne classe jamais un paquet inconnu en SÛR.** Un paquet
non identifié est RISQUÉ par défaut, et l'agent interroge `dumpsys package` avant
de demander à l'utilisateur.

### 7.5 Le questionnaire

Court, posé au moment utile et non en bloc au départ, sur le modèle de cleanyourtv :

1. CarPlay seulement, ou **aussi Android Auto** ? (jamais supposé)
2. L'audio et les appels passent-ils par le boîtier ou par le Bluetooth de la
   voiture ?
3. On garde les mises à jour du firmware ?
4. On garde l'assistant vocal ?

Tout le reste se décide sans l'utilisateur.

### 7.6 Les lots et la vérification à deux étages

- Lots **petits**, jamais un gros paquet de désactivations. Tant qu'il n'est pas
  prouvé sur matériel que le service d'accessibilité du mirroring se lie bien **hors
  voiture** (il peut n'être actif qu'en présence d'un hôte USB), la vérification de
  bureau ne prouve rien sur le tactile : dans ce cas, **une famille de paquets par
  cycle en voiture**, pas davantage.
- Entre chaque lot : `sync`, attente, redémarrage, et **contrôle de survie**.
- **Étage bureau** (automatisable) : le service d'accessibilité du mirroring est
  toujours actif, le Wi-Fi remonte, l'ADB répond, une capture d'écran est
  obtenue. Tant que ces quatre points ne sont pas verts, **on n'enchaîne pas**.
- **Étage voiture** (humain, à la fin) : le doigt sur l'écran, CarPlay qui
  s'appaire, l'audio, les appels, le temps entre le démarrage du moteur et
  l'affichage.

Le prompt doit dire noir sur blanc qu'**un tap injecté n'est pas une preuve de
tactile** — exactement la règle d'honnêteté de cleanyourtv (« an injected key is
not proof »).

### 7.7 Mesure

Avant / après, pour donner un chiffre et non une impression : RAM libre, nombre de
processus, température en régime, et **le délai entre la mise sous tension et
CarPlay affiché** — c'est la métrique que l'utilisateur ressent vraiment.

### 7.8 Récupération

Une page par modèle, `recovery/<fabricant>-<modèle>.md`, **écrite seulement après
qu'un probe a identifié le SoC** — jamais à l'avance. Trois niveaux :

1. `restore.sh` rejoue le profil et réactive tout.
2. Remise à zéro de l'appareil par ses propres moyens (combinaison de boutons,
   effacement des données).
3. **EDL en dernier recours — Qualcomm uniquement** (mode 9008). Documenté, jamais
   automatisé : aucun firmware ni loader n'est redistribué, et le dépôt ne propose
   jamais d'écrire une image ni de toucher au bootloader ou au modem. Un boîtier
   Amlogic, Allwinner ou MediaTek a une procédure entièrement différente : écrire
   une page EDL pour lui serait faux **et dangereusement crédible**.

### 7.9 Les réglages système, pas seulement les paquets

Désactiver des paquets ne suffit pas à tenir les promesses de démarrage et de
chauffe. Entrent donc dans le périmètre, **à condition stricte d'être sauvegardés et
rejoués par `restore.sh`** :

- les échelles d'animation (gain direct sur le ressenti au démarrage) ;
- la politique de mise en veille du Wi-Fi ;
- le rattachement automatique au Wi-Fi domestique, qui sert directement le chemin 2
  du §7.1 et rend le boîtier joignable au bureau.

Le profil gagne donc un `settings.json` à côté de sa liste de paquets. Limite
explicite : on s'en tient à des clés `settings put` avec couple
sauvegarde/restauration. Pas de bricolage sur les listes blanches de veille
(`deviceidle`) ni sur les gouverneurs.

### 7.10 Travailler sans matériel sacrifiable

Puisqu'aucun boîtier ne peut être perdu, le projet se construit **sur des fixtures
d'abord** : des sorties réelles de `getprop`, `pm list packages -f`,
`dumpsys package`, `dumpsys accessibility`, `dumpsys dropbox` capturées sur le vrai
appareil **en lecture seule**, versionnées (anonymisées) et utilisées pour
développer et tester toute la classification hors matériel.

Trois règles qui en découlent :

1. **La première session sur le boîtier réel ne désactive rien.** Elle fait le probe,
   le diag, capture les fixtures, et s'arrête là. C'est aussi ce qui donne la
   première réponse utile à Killian sur ses reboots, sans prendre le moindre risque.
2. **Aucune désactivation avant que la restauration soit prouvée.** On vérifie que
   `restore.sh` réactive bien un paquet manifestement inoffensif, aller-retour
   complet avec redémarrage, avant de toucher à quoi que ce soit d'autre.
3. **La page de récupération du modèle est écrite avant le premier lot**, pas après.
   Si l'EDL est la seule issue sur ce SoC, on veut l'avoir lue et comprise avant
   d'en avoir besoin.

---

## 8. Pile technique (choix de l'auteur du document)

- **Python 3** pour les outils, **shell** pour les enveloppes, **Markdown** pour les
  références et les profils.
- **Pas de Java**, puisqu'il n'y a pas de launcher.
- **Réutilisation du client ADB pur Python de cleanyourtv** (`tools/tv.py`, MIT),
  adapté et attribué dans le README. Il évite d'exiger le binaire `adb` et fait
  gagner une semaine. Alternative acceptée : `adb` du SDK si présent.
- Pas de dépendance lourde ; `requirements.txt` minimal.

**Langue : les deux.** L'**anglais fait foi** — c'est la langue du code, des
commentaires, de `AGENTS.md`, des `references/`, des profils et des pages de
récupération, celle de cleanyourtv dont le projet hérite, et celle des contributeurs
qui verseront des profils de modèles que Killian ne possède pas. Le **français
couvre ce que l'utilisateur touche** : `README.fr.md` et `PROMPT.fr.md`, à l'image du
`README.fr.md` de cleanyourtv. Règle anti-dérive : quand les deux divergent,
l'anglais gagne, et une modification de `PROMPT.md` n'est complète que si
`PROMPT.fr.md` suit dans la même PR.

## 9. Forme du dépôt

```
PROMPT.md                  le texte à coller dans Claude Code — l'interface réelle
AGENTS.md                  règles non négociables pour l'agent (+ CLAUDE.md qui l'importe)
README.md                  ce que c'est, ce que ce n'est pas, attribution cleanyourtv
tools/                     probe, diag, disable, restore, check, screenshot
references/
  classify.md              jamais / risqué / sûr, avec les motifs
  diag.md                  les sources de preuve et leur lecture
  families.md              Android vs dongle Linux, comment distinguer
  power-test.md            mesure électrique manuelle, optionnelle
profiles/<marque-modèle>/
  probe.json               modèle, SoC, Android, build
  packages.txt             état initial + liste de désactivation
  settings.json            réglages sauvegardés (§7.9)
  mesures.md               avant / après
recovery/<marque-modèle>.md  écrite après probe, EDL si Qualcomm
.gitignore                 bugreports et sorties brutes, jamais versionnés
docs/
CONTRIBUTING.md            comment verser un profil anonymisé
LICENSE                    MIT
```

## 10. Sécurité

Le README et le prompt doivent dire, sans dramatiser et une seule fois : sur
beaucoup de ces boîtiers l'ADB est ouvert en permanence et tourne en root ; ne les
branchez que sur un réseau de confiance. En fin d'opération, l'agent propose de
refermer le débogage et **vérifie que le port est effectivement fermé** — seule la
vérification compte, pas l'état apparent du réglage.

## 11. Ce qui est laissé au développeur

- Le format exact des fichiers de profil et de liste de désactivation.
- La stratégie de détection de la pile de mirroring sur un boîtier inconnu
  (heuristique par service d'accessibilité + paquets détenant les permissions
  d'affichage et d'USB) : c'est la partie la plus délicate, et elle devra être
  revue après le premier matériel réel.
- Le découpage précis des lots.
- La forme du rapport de diag.
- Les tests : au minimum des fixtures de sorties `dumpsys` / `getprop` pour tester
  la classification sans matériel.

## 12. Validation

Rien ne part en production sans un passage sur **au moins un boîtier réel** de
Killian. Le dépôt doit annoncer honnêtement le matériel sur lequel il a été testé
et ne jamais laisser croire à une couverture plus large — c'est ce qui manque à
tous les dépôts voisins recensés.

Jalons, dans cet ordre, vu la contrainte de non-sacrifiabilité :

| | Contenu | Matériel |
|---|---|---|
| **M0** | probe + diag, strictement en lecture seule ; capture des fixtures | oui, sans risque |
| **M1** | classification, tests sur fixtures, `restore.sh` | non |
| **M2** | aller-retour de restauration prouvé sur un paquet inoffensif | oui |
| **M3** | premiers lots SÛR, vérification à deux étages | oui |
| **M4** | questionnaire, lots RISQUÉ, mesures avant/après | oui |
| **M5** | publication, `CONTRIBUTING.md`, appel à profils | — |

M0 a une valeur propre : il répond déjà à la question de départ (« pourquoi ça
reboot ») sans avoir rien modifié.

## 13. Prior art consulté

- [Gathin23/cleanyourtv](https://github.com/Gathin23/cleanyourtv) — le modèle :
  mécanique `pm disable-user`, pilotage par agent via `PROMPT.md`/`AGENTS.md`,
  garde-fou HOME, profils par modèle. MIT.
- [teab0www/carlinkit-tbox-ultra2-recovery](https://github.com/teab0www/carlinkit-tbox-ultra2-recovery)
  — source des pièges tactile / APEX / `sync`, et de la procédure EDL. Un seul
  modèle couvert.
- [hamza39460/headunit-debloat-skill](https://github.com/hamza39460/headunit-debloat-skill)
  — skill Claude Code pour autoradios Android, même mécanique, testé sur un seul
  appareil (PX5). Source de l'avertissement ADB root.
- [itisAntoine/cleanyourcar](https://github.com/itisAntoine/cleanyourcar) — homonyme
  trompeur : le debloat y est explicitement non disponible. À ne pas confondre.
- [jamal2362/Mini-Car-Launcher](https://github.com/jamal2362/Mini-Car-Launcher) —
  launcher pour AI Box ; hors périmètre ici.
