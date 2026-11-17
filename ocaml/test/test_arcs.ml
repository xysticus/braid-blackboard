(* Tests de l'étape 4 : films d'arcs et diagramme de courbes, comparés au Python (reference_arcs.json, écrit par
   genere_reference_arcs.py). *)

open Ardoise
open Geometrie
open Triangulation
module J = Yojson.Safe.Util

let reference = lazy (Yojson.Safe.from_file "reference_arcs.json")
let champ nom j = J.member nom j
let entiers j = List.map J.to_int (J.to_list j)
let reels j = List.map J.to_number (J.to_list j)
let point_de j = match reels j with [ x; y ] -> { x; y } | _ -> failwith "point"
let points_de j = Array.of_list (List.map point_de (J.to_list j))
let matrice_de j = Array.of_list (List.map (fun l -> Array.of_list (reels l)) (J.to_list j))

let noeud_de j =
  match J.to_list j with
  | [ s ] -> Sommet (J.to_int s)
  | [ u; v; w ] -> Sur_arete (Arete.v (J.to_int u) (J.to_int v), J.to_number w)
  | _ -> failwith "noeud"

let courbes_de j = List.map (fun c -> List.map noeud_de (J.to_list c)) (J.to_list j)

let triangles_de j =
  List.map (fun t -> match entiers t with [ a; b; c ] -> Triangle.v a b c | _ -> failwith "triangle") (J.to_list j)

let proches nom tolerance a b =
  if Float.abs (a -. b) > tolerance then Alcotest.failf "%s : %.17g au lieu de %.17g" nom b a

let verifie_matrice nom tolerance attendu obtenu =
  Alcotest.(check int) (nom ^ " : lignes") (Array.length attendu) (Array.length obtenu);
  Array.iter2 (Array.iter2 (proches nom tolerance)) attendu obtenu

let verifie_courbes nom tolerance attendu obtenu =
  Alcotest.(check int) (nom ^ " : nombre de courbes") (List.length attendu) (List.length obtenu);
  List.iteri
    (fun k (c, c') ->
      if List.length c <> List.length c' then
        Alcotest.failf "%s, courbe %d : %d noeuds au lieu de %d" nom k (List.length c') (List.length c);
      List.iter2
        (fun n n' ->
          match (n, n') with
          | Sommet s, Sommet s' when s = s' -> ()
          | Sur_arete (e, w), Sur_arete (e', w') when e = e' -> proches (Printf.sprintf "%s, courbe %d" nom k) tolerance w w'
          | _ -> Alcotest.failf "%s, courbe %d : arêtes traversées différentes" nom k)
        c c')
    (List.combine attendu obtenu)

let entiers_des_mots mots = List.map (fun r -> Tresses.entiers_de_mot (r : Tresses.Reduit.t :> Tresses.mot_de_fn)) mots

(* L'état du film comparé à un état du Python : maillage, courbes, places, mots et rubans. La référence est
   calculée avec l'ordre de recherche des arêtes à retourner de l'OCaml (voir genere_reference_arcs.py) : sans lui,
   l'ordre d'un set Python change les courbes de quelques pour cent d'arête, et parfois la triangulation. *)
let verifie_etat nom tolerance attendu (film : Arcs.t) =
  let pos = points_de (champ "pos" attendu) in
  Alcotest.(check int) (nom ^ " : sommets") (Array.length pos) (Array.length film.maillage.pos);
  Array.iter2 (fun p q -> proches (nom ^ " : positions") 1e-9 (norme (p -: q)) 0.) pos film.maillage.pos;
  if List.sort compare (triangles_de (champ "triangles" attendu)) <> List.sort compare (Maillage.triangles film.maillage) then
    Alcotest.failf "%s : triangles différents" nom;
  verifie_courbes nom tolerance (courbes_de (champ "courbes" attendu)) film.courbes;
  Alcotest.(check (list int)) (nom ^ " : places") (entiers (champ "places" attendu)) (Array.to_list film.places);
  Alcotest.(check (list (list int))) (nom ^ " : mots") (List.map entiers (J.to_list (champ "mots" attendu)))
    (entiers_des_mots (Arcs.mots film));
  List.iteri
    (fun k r ->
      let p = Arcs.ruban film k in
      Alcotest.(check int) (Printf.sprintf "%s, ruban %d : points" nom k) (J.to_int (champ "n" r)) (Array.length p);
      let somme = Array.fold_left ( +: ) { x = 0.; y = 0. } p in
      let s = point_de (champ "somme" r) in
      proches (Printf.sprintf "%s, ruban %d : somme" nom k) (1e-9 *. float (Array.length p)) (norme (s -: somme)) 0.)
    (J.to_list (champ "rubans" attendu))

let films () = J.to_list (champ "films" (Lazy.force reference))
let tresse_de f = Tresses.tresse_de_entiers (entiers (champ "tresse" f))

let cree f =
  let tresse = tresse_de f in
  match J.to_string (champ "methode" f) with
  | "rubans" -> Arcs.cree ~ecart_fixes:30. tresse
  | "rubans_gauche" -> Arcs.cree ~fixes:Arcs.Gauche tresse
  | "arcs" -> Arcs.cree tresse
  | "diagramme" -> Arcs.cree_diagramme tresse
  | m -> failwith m

let nom f = J.to_string (champ "methode" f) ^ " " ^ String.concat "," (List.map string_of_int (entiers (champ "tresse" f)))

let test_pchip () =
  List.iter
    (fun cas ->
      let y = matrice_de (champ "y" cas) in
      let m = Arcs.pchip y in
      verifie_matrice "pentes" 1e-12 (matrice_de (champ "pentes" cas)) m;
      let v = Arcs.hermite y m (J.to_number (champ "t" cas)) in
      List.iteri (fun j a -> proches "hermite" 1e-12 a v.(j)) (reels (champ "valeur" cas)))
    (J.to_list (champ "pchip" (Lazy.force reference)))

(* Le constructeur : largeurs, maillage à bord convexe (indices des trous), arcs de départ découpés et tendus. *)
let test_depart f () =
  List.iter
    (fun f ->
      let film = cree f and d = champ "depart" f in
      let nom = nom f in
      verifie_matrice (nom ^ " : largeurs") 1e-14 (matrice_de (champ "largeurs" d)) film.largeurs;
      verifie_matrice (nom ^ " : pentes") 1e-14 (matrice_de (champ "pentes" d)) film.pentes;
      List.iter2
        (fun t attendu -> List.iteri (fun j a -> proches (nom ^ " : places") 1e-9 a (Arcs.places_au_temps film t).(j)) (reels attendu))
        [ 0.; 0.3; 1.5; float (List.length (tresse_de f)) ]
        (J.to_list (champ "places_au_temps" d));
      Alcotest.(check (list int)) (nom ^ " : voyageurs") (entiers (champ "voyageurs" d)) (Array.to_list film.voyageurs);
      Alcotest.(check (list int)) (nom ^ " : fixes") (entiers (champ "fixes" d)) (Array.to_list film.fixes);
      verifie_etat nom 1e-9 d film)
    [ f ]

(* Chaque lettre jouée en OCaml depuis l'état du Python redonne l'état suivant du Python. *)
let test_lettre f () =
  List.iter
    (fun f ->
      let depart = cree f in
      let etats = Array.of_list (champ "depart" f :: J.to_list (champ "etats" f)) in
      List.iteri
        (fun k sigma ->
          let e = etats.(k) in
          let film =
            { depart with
              maillage = Maillage.cree (points_de (champ "pos" e)) (triangles_de (champ "triangles" e));
              courbes = courbes_de (champ "courbes" e);
              places = Array.of_list (entiers (champ "places" e));
              numero = k }
          in
          verifie_etat (Printf.sprintf "%s, lettre %d" (nom f) (k + 1)) 1e-9 etats.(k + 1) (Arcs.lettre ~images:12 film sigma))
        (tresse_de f))
    [ f ]

(* Tout le film en OCaml : mêmes mots à chaque image clé que le Python, et que l'action d'Artin. *)
let test_film_entier () =
  List.iter
    (fun f ->
      let tresse = tresse_de f in
      let _ =
        List.fold_left
          (fun (film, k) sigma ->
            let film = Arcs.lettre ~images:12 film sigma in
            let attendu = List.nth (J.to_list (champ "etats" f)) k in
            Alcotest.(check (list (list int))) (Printf.sprintf "%s, mots %d" (nom f) (k + 1))
              (List.map entiers (J.to_list (champ "mots" attendu))) (entiers_des_mots (Arcs.mots film));
            (film, k + 1))
          (cree f, 0) tresse
      in
      ())
    (films ());
  List.iter
    (fun t ->
      let t = Tresses.tresse_de_entiers t in
      Alcotest.(check bool) "verifie_arcs" true (Arcs.verifie_arcs ~ecart_fixes:30. t);
      Alcotest.(check bool) "verifie_arcs, à gauche" true (Arcs.verifie_arcs ~fixes:Arcs.Gauche t);
      Alcotest.(check bool) "verifie_diagramme" true (Arcs.verifie_diagramme t))
    [ [ 4; 3; -1; -1; 2; -4; 1 ]; [ 1; -2; 1; -2; 1; -2; 3; -1; 2 ] ]

let () =
  Alcotest.run "arcs"
    [ ("pchip", [ Alcotest.test_case "comme le Python" `Quick test_pchip ]);
      ("départ", List.map (fun f -> Alcotest.test_case (nom f) `Quick (test_depart f)) (films ()));
      ("une lettre", List.map (fun f -> Alcotest.test_case (nom f) `Quick (test_lettre f)) (films ()));
      ("film", [ Alcotest.test_case "film entier" `Quick test_film_entier ]) ]
