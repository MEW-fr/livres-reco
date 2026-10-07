# Évaluation du MVP

_Rapport généré le 7 octobre 2026 à 15:34 par `python -m src.evaluate`, sur `data/books.db`._

## Synthèse

| Critère | Mesure | Verdict |
|---|---|---|
| Catalogue ≥ 500 livres uniques | 1290 livres | ✅ atteint |
| Recherche : livre visé dans le top 5 pour ≥ 15/20 | 15/20 | ✅ atteint |
| Livres proches : 5 résultats distincts expliqués | 0 échec(s) sur 30 | ✅ atteint |
| « Choisis pour toi » : 5 résultats expliqués | 0 échec(s) sur 46 profils | ✅ atteint |
| Temps de réponse < 3 s (objectif CDC < 1 s) | p95 max 6 ms, 0 erreur(s) | ✅ atteint (objectif < 1 s atteint) |
| Cohérence humaine ≥ 3/5 par profil | 8 profils à juger | ⏳ à remplir (docs/evaluation_humaine.md) |
| Diversité (indicatif) | 36 % de catégories distinctes en moyenne, 0 livre(s) passe-partout | ℹ️ sans seuil |

## 1. Catalogue

- Livres non masqués (indexés) : **1290**
- Livres uniques (titre + premier auteur, sans accents ni casse) : **1290** (critère ≥ 500)
- Avec au moins un thème : 971 (75.3 %)
- Avec une ambiance : 521 (40.4 %)

### Répartition par catégorie principale

| Catégorie | Livres | Part |
|---|---|---|
| romance | 218 | 16.9 % |
| thriller | 176 | 13.6 % |
| policier | 156 | 12.1 % |
| science-fiction | 150 | 11.6 % |
| essai | 99 | 7.7 % |
| dystopie | 95 | 7.4 % |
| biographie | 85 | 6.6 % |
| fantastique | 83 | 6.4 % |
| littérature générale | 74 | 5.7 % |
| aventure | 57 | 4.4 % |
| horreur | 52 | 4.0 % |
| roman historique | 45 | 3.5 % |

### Thèmes et ambiances

| Thème | Livres |
|---|---|
| crime | 276 |
| famille | 260 |
| mémoire | 243 |
| secret | 225 |
| amour | 158 |
| science | 138 |
| société | 110 |
| voyage | 101 |
| deuil | 101 |
| initiation | 91 |
| guerre | 80 |
| nature | 79 |
| art | 63 |
| amitié | 54 |
| survie | 45 |

| Ambiance | Livres |
|---|---|
| tendue | 165 |
| sombre | 95 |
| légère | 79 |
| épique | 65 |
| poétique | 59 |
| intimiste | 58 |

## 2. Retrouver un livre

20 requêtes de `tests/fixtures/recherche_20.json`, écrites à partir de livres tirés au hasard dans le catalogue (4 par type d'imperfection). Recherche sans filtre, même fonction que `/recherche` (`engine.find_book`). **Score : 15/20** (critère ≥ 15).

| Type | Requête | Livre visé | Rang | Résultats | Top 5 |
|---|---|---|---|---|---|
| minuscules | `texaco` | Texaco | 1 | 1 | ✅ |
| minuscules | `la route` | La Route | 1 | 1 | ✅ |
| minuscules | `gloutons et dragons` | Gloutons et Dragons (Tome 1) | 1 | 1 | ✅ |
| minuscules | `le mystère du fiacre` | Le Mystère du Fiacre | 1 | 1 | ✅ |
| sans accents | `la science experimentale` | La science expérimentale | 1 | 1 | ✅ |
| sans accents | `giraudoux europeen` | Giraudoux européen de l'entre-deux-guerres | 1 | 1 | ✅ |
| sans accents | `les francaises ont le regard triste` | Les françaises ont le regard triste | 1 | 1 | ✅ |
| sans accents | `l'epouse volee` | La famille Vallerand (Tome 1) - L’épouse volée | absent | 0 | ❌ |
| titre partiel | `salauds devront` | Les Salauds devront payer | 1 | 1 | ✅ |
| titre partiel | `pension caron` | La Pension Caron - Tome 2 | 1 | 1 | ✅ |
| titre partiel | `trois royaumes` | La Guerre des Trois Royaumes | 1 | 1 | ✅ |
| titre partiel | `mythe et politique` | Entre mythe et politique | 1 | 1 | ✅ |
| auteur seul | `denis johnson` | Fiskadoro | 1 | 1 | ✅ |
| auteur seul | `mayoux` | Bien Paraître | 1 | 1 | ✅ |
| auteur seul | `marc ferro` | De Russie et d'ailleurs | 1 | 1 | ✅ |
| auteur seul | `rebecca crowley` | Secrets de vestiaires (Tome 1) - Sous contrat | 4 | 4 | ✅ |
| faute d'une lettre | `le blues de l'echymose` | Le Blues de l'ecchymose | absent | 0 | ❌ |
| faute d'une lettre | `deux pas vers demin` | Deux pas vers demain | absent | 0 | ❌ |
| faute d'une lettre | `nos terres sont notre vye` | Nos terres sont notre vie | absent | 0 | ❌ |
| faute d'une lettre | `courtisanne d'un soir` | Courtisane d’un soir | absent | 0 | ❌ |

Par type : minuscules 4/4, sans accents 3/4, titre partiel 4/4, auteur seul 4/4, faute d'une lettre 0/4.

## 3. Recommandations

- `similar_books` sur 30 livres tirés au hasard (graine 2026) : 5 résultats distincts, sans le livre source, chacun expliqué par « Recommandé pour … ». **Échecs : 0.**
- « Choisis pour toi » (`recommend` avec filtres du compte, hors bibliothèque) pour les 46 profils de démo : 5 résultats distincts expliqués. **Échecs : 0.**

## 4. Performance

Client de test Flask sur `data/books.db`, connecté avec un profil de démo ; 50 appels par page après un appel de chauffe (chargement de l'index). Les requêtes de recherche reprennent celles de la section 2, les fiches sont tirées au hasard. Critère < 3 s, objectif du cahier des charges < 1 s.

| Page | Médiane | p95 | Erreurs | Verdict |
|---|---|---|---|---|
| /accueil | 6 ms | 6 ms | 0 | ✅ < 1 s |
| /recherche?q=… | 2 ms | 2 ms | 0 | ✅ < 1 s |
| /livre/<id> | 3 ms | 3 ms | 0 | ✅ < 1 s |
| /explorer | 5 ms | 5 ms | 0 | ✅ < 1 s |

## 5. Cohérence humaine

Grille dans `docs/evaluation_humaine.md` : 8 profils de démo (le premier de chaque famille, plus le deuxième des 2 familles les plus peuplées), leurs réponses clés et leurs 5 recommandations « Choisis pour toi ». À remplir par les membres du groupe ; critère : au moins 3/5 jugées cohérentes par profil.

| Profil | Libellé | Famille |
|---|---|---|
| nour | Émotions & liens | psychologie |
| aline | Suspense & tension | suspense |
| theo | Futurs possibles | imaginaire |
| pierre | Grandes épopées | histoire |
| fatou | Esprits curieux | réel et idées |
| camille | Éclectique | éclectique |
| clement | Âme littéraire | psychologie |
| karim | Suspense & tension | suspense |

## 6. Diversité

- Part des catégories principales distinctes dans les 5 recommandations : **36 %** en moyenne sur 46 profils (minimum 20 %, soit 1 catégorie(s) sur 5).
- Livres distincts recommandés : 179 pour 230 places.
- Livres « passe-partout » (recommandés à plus de 10 profils) : **0** (0.0 % des livres recommandés).

Livres les plus recommandés :

| Livre | Profils |
|---|---|
| Filles de la Pluie | 4 |
| Première ligne | 4 |
| Quelqu'un ment | 3 |
| Les filles perdues de Stillwater | 3 |
| La fabuleuse aventure de Cristobal Colon | 3 |
