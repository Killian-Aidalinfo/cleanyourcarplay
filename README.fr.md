# cleanyourcarplay

**Savoir pourquoi ton boîtier CarPlay Android plante, puis le réduire au seul
métier pour lequel tu t'en sers.**

Ces boîtiers — Carlinkit TBox/Ultra, Ottocast et les nombreux clones — sont de
vrais appareils Android vendus pour faire une chose : mettre du CarPlay sans fil
sur une voiture qui n'a que le filaire. La plupart des gens n'y ouvrent jamais
une application. Pourtant ils arrivent avec un Play Store, un navigateur, des
lecteurs multimédias, une boutique du fabricant et de la télémétrie, le tout en
concurrence pour 2 Go de RAM derrière ta navigation.

Ce toolkit fait deux choses, dans cet ordre :

1. **Le diagnostic.** Il lit pourquoi ton boîtier a redémarré la dernière fois,
   ce qui a planté, à quelle température il est monté et ce qu'a fait son
   alimentation. C'est en premier parce qu'une bonne part de ces redémarrages
   est **électrique** : les ports USB de voiture et les prises allume-cigare
   délivrent souvent moins de 1 A, et la tension s'effondre au démarrage du
   moteur. Aucun nettoyage ne corrige ça, et tu mérites de le savoir avant de
   commencer.
2. **Le nettoyage.** Il désactive tout ce qui n'est pas nécessaire pour
   démarrer, monter le Wi-Fi et le Bluetooth, s'appairer au téléphone et faire
   tourner le mirroring. Rien n'est désinstallé. Tout est réversible.

Tout passe par ADB depuis ton ordinateur. Pas de root. Pas de flash. Rien
d'écrit dans `/system`.

## État du projet — à lire en premier

**Ce toolkit n'a pas encore tourné sur un appareil réel.** Le matériel est
attendu le 2026-11-27. Les noms de paquets, de propriétés et de chemins système
présents dans ce dépôt viennent de rapports documentés sur des appareils
comparables, pas d'un boîtier que ce projet aurait touché. Le dossier
`profiles/` est vide précisément pour cette raison, et il ne listera jamais que
des boîtiers réellement testés.

La plupart des dépôts du domaine annoncent une large compatibilité sur la foi
d'un seul appareil. Celui-ci te dira exactement ce qu'il a vu.

Il a en revanche tourné de bout en bout contre un vrai Android : un émulateur
jetable dans une VM, voir `tests/emu/`. Cela prouve que le code fonctionne face
à un `adbd`, un `pm` et un `settings` vivants, et cela a mis au jour cinq bugs
qu'aucune relecture n'aurait trouvés. Cela ne prouve rien sur un boîtier
CarPlay : un émulateur n'a ni pile de mirroring, ni firmware constructeur, ni
voiture.

## Comment on s'en sert

Tu ne lis pas ce README pour utiliser le toolkit, et tu ne tapes pas ses
commandes. Tu colles une URL dans Claude Code et tu réponds à quelques
questions :

```
https://raw.githubusercontent.com/Killian-Aidalinfo/cleanyourcarplay/main/PROMPT.fr.md
```

L'agent se connecte au boîtier, lance le diagnostic en lecture seule, te dit ce
qu'il a trouvé, te pose quatre questions et fait le reste. Chaque geste est
enregistré : une commande remet tout en place.

On te demandera : tu utilises **Android Auto** en plus de CarPlay ? les appels
et l'audio passent par le boîtier ou par le Bluetooth de la voiture ? on garde
les mises à jour du firmware ? on garde l'assistant vocal ?

## Ce que ce n'est pas

- **Pas un launcher.** Tu ne regardes jamais l'interface Android de cet
  appareil, donc aucun effort n'y est consacré. Si tu veux un launcher pour une
  AI Box dont tu te sers vraiment comme d'une box Android, regarde
  [Mini-Car-Launcher](https://github.com/jamal2362/Mini-Car-Launcher).
- **Pas pour les dongles CarPlay sous Linux.** Les petits adaptateurs —
  Carlinkit 3.0/4.0, CPC200-CCPA, Ottocast U2-X — tournent sous Linux embarqué.
  Ni ADB, ni paquets, rien à désactiver. Ce toolkit **les détecte et s'arrête**,
  et te renvoie vers [catplay](https://github.com/catplay-labs/catplay).
- **Pas un kit de root ou de flash.** Aucun firmware, aucun loader, aucune
  intervention sur le bootloader, et rien dans ce dépôt n'écrit jamais d'image.
- **Pas de rétro-ingénierie du protocole CarPlay.** Voir
  [ludwig-v/wireless-carplay-dongle-reverse-engineering](https://github.com/ludwig-v/wireless-carplay-dongle-reverse-engineering).

## Le risque, dit franchement

Une TV que tu casses, tu la répares depuis son propre menu Réglages avec sa
propre télécommande. **Ce boîtier n'a ni l'un ni l'autre.** Il n'a pas d'écran à
lui — il s'affiche dans la fenêtre CarPlay de ta voiture — pas de télécommande,
et aucun menu Réglages atteignable. Ton seul retour en arrière, c'est ADB par le
réseau.

Deux erreurs précises sont donc bien plus graves ici qu'elles n'en ont l'air :

- **Désactiver la pile de mirroring.** Sur au moins un appareil documenté, le
  paquet qui héberge le service d'accessibilité réinjectant tes appuis dans
  CarPlay est `com.carsyso.main`. Désactive-le : le boîtier démarre
  parfaitement, l'image s'affiche, et l'écran ne répond plus à ton doigt. Rien
  ne « plante ». Tu ne peux simplement plus rien faire.
- **Désactiver les paquets APEX sous Android 13+.**
  `com.android.adservices.api`, `com.android.sdksandbox`,
  `com.android.federatedcompute.services` et
  `com.android.ondevicepersonalization.services` donnent une boucle de
  démarrage, une LED clignotante, pas de Wi-Fi et pas d'ADB. La seule issue
  documentée est le mode EDL Qualcomm avec un loader firehose tiers.

Ce toolkit **refuse** donc ces paquets. Il n'y a pas d'option pour passer
outre, et demander gentiment n'en créera pas. Un paquet inconnu est traité comme
risqué, jamais comme sûr.

Un dernier piège, bête à commettre : après `pm disable-user`, lance
`adb shell sync` et attends avant de redémarrer, sinon tout ton lot disparaît
silencieusement.

## Sécurité

Sur beaucoup de ces boîtiers, l'ADB est ouvert sur le port 5555 à chaque
démarrage quoi que disent les réglages, et il tourne en root. N'importe qui sur
le même Wi-Fi peut tout faire sur l'appareil. Garde-le sur un réseau de
confiance, et laisse le toolkit refermer le débogage à la fin — il vérifie que
le port est réellement fermé au lieu de croire l'interrupteur.

## Organisation du dépôt

| Chemin | Ce que c'est |
|---|---|
| `PROMPT.md` / `PROMPT.fr.md` | la vraie interface : à coller dans Claude Code |
| `AGENTS.md` | les règles que l'agent n'a pas le droit d'enfreindre |
| `tools/` | les mains de l'agent : sonder, diagnostiquer, désactiver, restaurer |
| `references/` | classification, sources de preuve, familles d'appareils |
| `profiles/<marque-modèle>/` | ce qu'un appareil réel a rapporté, anonymisé |
| `recovery/<marque-modèle>.md` | comment récupérer ce modèle, écrit après un probe |

## Crédit

L'approche, et le client ADB en Python pur que ce projet adapte, viennent de
[Gathin23/cleanyourtv](https://github.com/Gathin23/cleanyourtv) (MIT) — la même
idée pour les TV Android. Les cas de brique documentés viennent de
[teab0www/carlinkit-tbox-ultra2-recovery](https://github.com/teab0www/carlinkit-tbox-ultra2-recovery),
et l'avertissement sur l'ADB en root de
[hamza39460/headunit-debloat-skill](https://github.com/hamza39460/headunit-debloat-skill).

MIT.
