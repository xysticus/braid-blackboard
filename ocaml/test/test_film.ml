(* Tests de l'étape 3 : tension, dessin, mouvement des trous, comparés au Python (reference_film.json, écrit par
   genere_reference_film.py). *)

open Ardoise
open Geometrie
open Triangulation
module J = Yojson.Safe.Util

let reference = lazy (Yojson.Safe.from_file "reference_film.json")
let champ nom j = J.member nom j
let entiers j = List.map J.to_int (J.to_list j)
let reels j = List.map J.to_number (J.to_list j)
let point_de j = match reels j with [ x; y ] -> { x; y } | _ -> failwith "point"
let points_de j = Array.of_list (List.map point_de (J.to_list j))

let noeud_de j =
  match J.to_list j with
  | [ s ] -> Sommet (J.to_int s)
  | [ u; v; w ] -> Sur_arete (Arete.v (J.to_int u) (J.to_int v), J.to_number w)
  | _ -> failwith "noeud"

let courbes_de j = List.map (fun c -> List.map noeud_de (J.to_list c)) (J.to_list j)

(* Écart maximal entre deux familles de courbes (en fraction d'arête), ou None si leurs structures diffèrent. *)
let ecart_courbes a b =
  let ecart_noeud n n' =
    match (n, n') with
    | Sommet s, Sommet s' when s = s' -> Some 0.
    | Sur_arete (e, w), Sur_arete (e', w') when e = e' -> Some (Float.abs (w -. w'))
    | _ -> None
  in
  let max_opt a b = match (a, b) with Some a, Some b -> Some (Float.max a b) | _ -> None in
  if List.length a <> List.length b then None
  else
    List.fold_left2
      (fun acc c c' ->
        if List.length c <> List.length c' then None
        else List.fold_left2 (fun acc n n' -> max_opt acc (ecart_noeud n n')) acc c c')
      (Some 0.) a b

let verifie_courbes nom tolerance attendu obtenu =
  match ecart_courbes attendu obtenu with
  | None -> Alcotest.fail (nom ^ " : structures différentes (arêtes traversées)")
  | Some e ->
    if e > tolerance then Alcotest.failf "%s : écart %g > %g" nom e tolerance

let disposition_de j =
  { Film.abscisses = Array.of_list (reels (champ "abscisses" j)); ecart = J.to_number (champ "ecart" j) }

(* Un film OCaml à partir des données fixes et d'un état du Python. *)
let film_de fixe etat =
  let dispositions j = Array.of_list (List.map disposition_de (J.to_list j)) in
  let triangles =
    List.map (fun t -> match entiers t with [ a; b; c ] -> Triangle.v a b c | _ -> failwith "triangle")
      (J.to_list (champ "triangles" etat))
  in
  { Film.hauteur = J.to_number (champ "hauteur" fixe);
    largeur = J.to_number (champ "largeur" fixe);
    nb_trous = J.to_int (champ "nb_trous" fixe);
    dispositions = dispositions (champ "dispositions" fixe);
    milieux = dispositions (champ "milieux" fixe);
    etape = J.to_int (champ "etape" etat);
    maillage = Maillage.cree (points_de (champ "pos" etat)) triangles;
    trous = Array.of_list (entiers (champ "trous" etat));
    clou = J.to_int (champ "clou" fixe);
    haut = Array.of_list (entiers (champ "haut" fixe));
    bas = Array.of_list (entiers (champ "bas" fixe));
    decalage_bas = J.to_number (champ "decalage_bas" fixe);
    place_du_clou = (match J.to_list (champ "place_du_clou" fixe) with [ j; f ] -> (J.to_int j, J.to_number f) | _ -> failwith "clou");
    y_axe = J.to_number (champ "y_axe" fixe);
    courbes = courbes_de (champ "courbes" etat) }

let films () = J.to_list (champ "films" (Lazy.force reference))
let tresse_de f = Tresses.tresse_de_entiers (entiers (champ "tresse" f))
let etats f = Array.of_list (J.to_list (champ "etats" f))
let entiers_des_mots mots = List.map (fun r -> Tresses.entiers_de_mot (r : Tresses.Reduit.t :> Tresses.mot_de_fn)) mots

let test_monotone () =
  List.iter
    (fun cas ->
      let obtenu = Film.monotone (reels (champ "valeurs" cas)) in
      List.iter2 (fun a b -> Alcotest.(check (float 1e-12)) "monotone" a b) (reels (champ "resultat" cas)) obtenu)
    (J.to_list (champ "monotone" (Lazy.force reference)))

let test_deux_arcs () =
  List.iter
    (fun cas ->
      let p nom = point_de (champ nom cas) in
      let attendu = points_de (champ "resultat" cas) in
      let obtenu = Tresses.deux_arcs (p "p0") (p "t0") (p "p1") (p "t1") in
      Alcotest.(check int) "nombre de points" (Array.length attendu) (Array.length obtenu);
      Array.iter2 (fun a b -> if norme (a -: b) > 1e-9 then Alcotest.failf "point à %g" (norme (a -: b))) attendu obtenu)
    (J.to_list (champ "deux_arcs" (Lazy.force reference)))

(* Un pas de tension depuis un état du Python, avec les réglages du film puis avec degagement et portee_sinus. *)
let test_tend () =
  List.iter
    (fun f ->
      Array.iteri
        (fun k etat ->
          match champ "tend" etat with
          | `Null -> ()
          | attendu ->
            let film = film_de (champ "fixe" f) etat in
            let ecart = film.Film.dispositions.(film.etape).ecart in
            verifie_courbes (Printf.sprintf "état %d" k) 1e-12 (courbes_de attendu) (Film.tend film 0.15 ecart).courbes;
            verifie_courbes (Printf.sprintf "état %d, portée" k) 1e-12 (courbes_de (champ "tend_portee" etat))
              (Film.tend ~degagement:2. ~portee_sinus:10. film 0.15 ecart).courbes)
        (etats f))
    (films ())

(* Les polylignes dessinées : nombre de points, sommes des coordonnées et un point sur 25. *)
let test_polylignes () =
  List.iter
    (fun f ->
      Array.iter
        (fun etat ->
          match champ "polylignes" etat with
          | `Null -> ()
          | resumes ->
            let film = film_de (champ "fixe" f) etat in
            List.iter2
              (fun r p ->
                Alcotest.(check int) "nombre de points" (J.to_int (champ "n" r)) (Array.length p);
                let somme = Array.fold_left ( +: ) { x = 0.; y = 0. } p in
                Alcotest.(check (float 1e-6)) "somme" 0. (norme (somme -: point_de (champ "somme" r)));
                Array.iteri
                  (fun j q -> Alcotest.(check (float 1e-9)) "échantillon" 0. (norme (q -: p.(25 * j))))
                  (points_de (champ "echantillon" r)))
              (J.to_list resumes) (Film.polylignes film))
        (etats f))
    (films ())

(* Sur chaque état du Python, les mots relus par l'OCaml (lissés ou non) sont ceux du Python et ceux de
   calcule_autofn_de_tresse. *)
let test_mots () =
  List.iter
    (fun f ->
      let tresse = tresse_de f in
      Array.iteri
        (fun k etat ->
          let film = film_de (champ "fixe" f) etat in
          let attendu = List.map entiers (J.to_list (champ "mots" etat)) in
          let algebre =
            Array.to_list (Tresses.calcule_autofn_de_tresse ~nb_trous:film.nb_trous (List.filteri (fun j _ -> j < k) tresse))
          in
          Alcotest.(check (list (list int))) "comme le Python" attendu (entiers_des_mots (Film.mots film));
          Alcotest.(check (list (list int))) "sans lissage" attendu (entiers_des_mots (Film.mots ~lisse:false film));
          Alcotest.(check (list (list int))) "comme l'algèbre" attendu (entiers_des_mots algebre))
        (etats f))
    (films ())

(* Une lettre jouée par l'OCaml depuis l'état k du Python, comparée à l'état k + 1 du Python. *)
let test_lettre () =
  let pire = ref 0. in
  List.iter
    (fun f ->
      let tresse = Array.of_list (tresse_de f) and etats = etats f in
      let images = Array.of_list (entiers (champ "images" f)) in
      Array.iteri
        (fun k sigma ->
          let film = film_de (champ "fixe" f) etats.(k) in
          let film, n = Film.lettre film sigma in
          let attendu = etats.(k + 1) in
          let nom = Printf.sprintf "lettre %d" (k + 1) in
          Alcotest.(check int) (nom ^ " : images") images.(k) n;
          Alcotest.(check int) (nom ^ " : étape") (J.to_int (champ "etape" attendu)) film.etape;
          Alcotest.(check (list int)) (nom ^ " : trous") (entiers (champ "trous" attendu)) (Array.to_list film.trous);
          (match ecart_courbes (courbes_de (champ "courbes" attendu)) film.courbes with
           | Some e -> pire := Float.max !pire e
           | None -> Alcotest.fail (nom ^ " : structures différentes"));
          verifie_courbes nom 1e-12 (courbes_de (champ "courbes" attendu)) film.courbes)
        tresse)
    (films ());
  Printf.printf "écart maximal après une lettre : %g (fraction d'arête)\n" !pire

(* Tout le film joué par l'OCaml seul, depuis l'état de départ : les mots relus après chaque lettre sont ceux de
   l'algèbre. *)
let test_film_entier () =
  List.iter
    (fun f ->
      let tresse = tresse_de f in
      let film0 = film_de (champ "fixe" f) (etats f).(0) in
      ignore
        (List.fold_left
           (fun (film, k) sigma ->
             let film, _ = Film.lettre film sigma in
             let algebre =
               Tresses.calcule_autofn_de_tresse ~nb_trous:film.nb_trous (List.filteri (fun j _ -> j <= k) tresse)
             in
             Alcotest.(check (list (list int)))
               (Printf.sprintf "mots après la lettre %d" (k + 1))
               (entiers_des_mots (Array.to_list algebre))
               (entiers_des_mots (Film.mots film));
             (film, k + 1))
           (film0, 0) tresse))
    (films ())

let () =
  Alcotest.run "film"
    [ ("outils", [ Alcotest.test_case "monotone" `Quick test_monotone; Alcotest.test_case "deux_arcs" `Quick test_deux_arcs ]);
      ( "comme le Python",
        [ Alcotest.test_case "tend" `Quick test_tend;
          Alcotest.test_case "polylignes" `Quick test_polylignes;
          Alcotest.test_case "mots" `Quick test_mots;
          Alcotest.test_case "une lettre" `Slow test_lettre ] );
      ("seul", [ Alcotest.test_case "film entier" `Slow test_film_entier ]) ]
