# Le prompt

Copie tout ce qui suit la ligne dans Claude Code (ou tout agent avec accès au
shell) et remplis le seul blanc. L'agent fait le reste et te pose quatre
questions en chemin.

## Avant de commencer

1. **Ton boîtier doit être une AI Box Android**, pas un dongle Linux. Si c'est
   un petit adaptateur avec une page web de configuration et pas d'Android,
   arrête-toi ici — voir [references/families.md](references/families.md). Le
   toolkit te le dira aussi, mais autant le savoir tout de suite.
2. **Active l'ADB.** Sur la plupart de ces boîtiers il est déjà actif : le
   firmware ouvre le port 5555 à chaque démarrage quoi que dise le réglage.
   Sinon, va dans Paramètres → À propos, tape sept fois sur le numéro de build,
   puis active le débogage USB et le débogage réseau.
3. **Fais rejoindre ton Wi-Fi domestique au boîtier**, une fois, depuis la
   voiture. Tout le reste se passe à ton bureau. Si ton boîtier expose l'ADB en
   USB, prends le câble — voir [docs/CONNECT.md](docs/CONNECT.md).
4. **Sache que la première passe ne change rien.** Elle lit, elle te dit ce
   qu'elle a trouvé, et elle s'arrête. C'est toi qui décides d'aller plus loin.

---

Je veux diagnostiquer et nettoyer mon boîtier CarPlay Android avec le toolkit
cleanyourcarplay.

Mon boîtier est : `<MARQUE ET MODÈLE ICI, ou « je ne sais pas »>`

Travaille sur l'appareil réel, étape par étape, et montre-moi ce que tu trouves
au fur et à mesure. Demande-moi avant tout ce qui dépend de mon usage. Ne
devine jamais le rôle d'un paquet.

**Récupérer le toolkit**

Clone https://github.com/Killian-Aidalinfo/cleanyourcarplay et lis `AGENTS.md`
avant de toucher à mon appareil. Les règles qu'il contient ne sont pas
négociables, et elles existent parce que cet appareil n'a ni écran, ni
télécommande, ni bouton reset : si tu casses son démarrage ou son Wi-Fi, ni toi
ni moi ne pouvons y revenir.

**Se connecter**

Trouve mon boîtier sur le réseau — ARP, mDNS, un scan du port 5555, ou
demande-moi l'adresse. Préfère l'USB si `adb devices` le voit par là : un câble
survit à un Wi-Fi qui ne remonte plus.

Si l'ADB demande une autorisation, préviens-moi : la fenêtre s'affiche sur
l'écran du boîtier, donc dans la voiture.

```bash
export BOX_HOST=<adresse>
python3 tools/box.py --probe
```

Si le probe dit que c'est un dongle Linux, arrête-toi et dis-le moi. Il n'y a
rien ici pour lui.

**Diagnostiquer d'abord — ça ne change rien**

```bash
python3 tools/diag.py --write
python3 tools/profile.py
```

Puis dis-moi, en français clair :

- pourquoi le boîtier a redémarré la dernière fois, et si ça ressemble à de
  l'électrique ou à du logiciel ;
- ce qui plante ;
- combien de mémoire est réellement libre ;
- à quelle température il a tourné.

Si les indices pointent vers une coupure d'alimentation, **dis-le avant qu'on
nettoie quoi que ce soit**, et explique-moi qu'un nettoyage ne corrigera pas un
problème d'alimentation. Mon boîtier est sur allume-cigare ou USB de voiture,
donc c'est une vraie possibilité, pas une formule. Renvoie-moi vers
`references/power-test.md` si ça vaut la peine de mesurer.

Arrête-toi là et laisse-moi lire. Cette première passe vaut le coup à elle
seule.

**Nettoyer**

Seulement si je dis de continuer.

Construis la liste à partir de ce qui est réellement installé, avec
`python3 tools/classify.py` et le `probe.json` de mon appareil. Ne réutilise pas
une liste d'un autre modèle.

Avant de toucher au groupe RISQUÉ, pose-moi ces quatre questions en checklist et
ne désactive que ce que je ne coche pas :

1. Est-ce que j'utilise **Android Auto** en plus de CarPlay ? (Pose la question.
   Ça dépend des téléphones de la maison, tu ne peux pas le savoir.)
2. Les appels et l'audio passent par le boîtier ou par le Bluetooth de la
   voiture ?
3. On garde les mises à jour du firmware ?
4. On garde l'assistant vocal ?

Puis travaille par **petits lots** :

```bash
tools/disable.sh <fichier-de-liste>
```

L'outil refuse les paquets NEVER tout seul. N'essaie pas de le contourner et ne
me demande pas d'autoriser une exception — il n'y a pas d'option, c'est voulu.

Après chaque lot, l'outil synchronise, attend, et lance un contrôle de survie.
Si quoi que ce soit revient rouge, **arrête et restaure.** Ne lance pas le lot
suivant.

Dis-moi franchement après chaque lot que le contrôle de bureau ne prouve **pas**
que le tactile fonctionne encore. Un tap injecté n'est pas un doigt sur l'écran
de la voiture.

**Vérifier**

Mesure avant et après : mémoire libre, nombre de processus, et le délai entre la
mise sous tension et l'apparition de CarPlay — c'est ce dernier que je ressens.

Puis envoie-moi en voiture avec une liste :

- l'écran répond à mon doigt ;
- CarPlay s'appaire et se connecte sans fil ;
- l'audio fonctionne, les appels aussi ;
- Android Auto marche encore, si j'ai dit que je m'en sers ;
- combien de temps entre le démarrage du moteur et CarPlay.

Si quelque chose cloche, `tools/restore.sh` remet tout en place.

**Terminer**

- Écris `profiles/<marque-modèle>/mesures.md` avec les chiffres avant/après.
- Écris `recovery/<marque-modèle>.md` **pour le SoC que tu as réellement
  trouvé**, pas depuis un modèle type. Si ce n'est pas du Qualcomm, pas de
  section EDL.
- Propose de refermer le débogage ADB, et vérifie que le port est vraiment
  fermé au lieu de croire l'interrupteur.
- Dis-moi ce que tu n'as pas pu établir. Je préfère un trou annoncé à une
  supposition assurée.

Tout ce que tu fais est réversible en une commande, et rien n'est désinstallé.
