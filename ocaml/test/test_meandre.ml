(* Tests de l'étape 3 bis : le méandre (tresses.py) et le constructeur du film (Film.__init__), comparés au Python
   (reference_meandre.json, écrit par genere_reference_meandre.py, et l'état de départ de reference_film.json). *)

open Ardoise
open Geometrie
open Triangulation
module J = Yojson.Safe.Util

let lit fichier = lazy (Yojson.Safe.from_file fichier)
let meandre = lit "reference_meandre.json"
let ref_film = lit "reference_film.json"
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
let etat_de j : Tresses.etat = { trous = Array.of_list (reels (champ "trous" j)); lacets = List.map (fun l -> Array.of_list (reels l)) (J.to_list (champ "lacets" j)) }
let tresse_de j = Tresses.tresse_de_entiers (entiers (champ "tresse" j))

let verifie_etat nom (attendu : Tresses.etat) (obtenu : Tresses.etat) =
  let proches a b = Array.length a = Array.length b && Array.for_all2 (fun x y -> Float.abs (x -. y) < 1e-12) a b in
  if not (proches attendu.trous obtenu.trous && List.length attendu.lacets = List.length obtenu.lacets
          && List.for_all2 proches attendu.lacets obtenu.lacets)
  then Alcotest.fail (nom ^ " : états différents")

(* Les assert de tresses.py. *)
let test_intervalles_assert () =
  let iv l = Tresses.intervalles (Tresses.mot_de_fn_de_entiers l) in
  Alcotest.(check (list int)) "[1]" [ 0; 1 ] (iv [ 1 ]);
  Alcotest.(check (list int)) "[-2]" [ 2; 1 ] (iv [ -2 ]);
  Alcotest.(check (list int)) "[1, 2, 3, 2, -3, -2, -1]" [ 0; 3; 1; 2; 3; 0 ] (iv [ 1; 2; 3; 2; -3; -2; -1 ]);
  List.iter
    (fun t ->
      let t = Tresses.tresse_de_entiers t in
      Alcotest.(check bool) "verifie" true (Tresses.verifie t);
      Alcotest.(check bool) "verifie_action" true (t = [] || Tresses.verifie_action t))
    [ []; [ 1; 1; 2; 2 ]; [ 4; 3; -1; -1; 2; -4; 1 ]; [ 1; -2; 1; -2; 1; -2; 3; -1; 2 ]; [ 1 ]; [ -1 ] ]

let tresses () = J.to_list (champ "tresses" (Lazy.force meandre))

let test_etats () =
  List.iteri
    (fun n cas ->
      let tresse = tresse_de cas and nb_trous = J.to_int (champ "nb_trous" cas) in
      let nom = Printf.sprintf "tresse %d" n in
      let images = Tresses.calcule_autofn_de_tresse ~nb_trous tresse in
      Alcotest.(check (list (list int))) (nom ^ " : intervalles")
        (List.map entiers (J.to_list (champ "intervalles" cas)))
        (Array.to_list (Array.map (fun m -> Tresses.intervalles (m : Tresses.Reduit.t :> Tresses.mot_de_fn)) images));
      verifie_etat (nom ^ " : etat_de_tresse") (etat_de (champ "etat" cas)) (Tresses.etat_de_tresse ~nb_trous tresse);
      Alcotest.(check bool) (nom ^ " : verifie") true (Tresses.verifie tresse);
      Alcotest.(check bool) (nom ^ " : verifie_action") true (Tresses.verifie_action tresse))
    (tresses ())

let test_agit () =
  List.iteri
    (fun n cas ->
      let tresse = tresse_de cas and nb_trous = J.to_int (champ "nb_trous" cas) in
      List.iteri
        (fun k action ->
          let nom = Printf.sprintf "tresse %d, lettre %d" n (k + 1) in
          let etat = Tresses.etat_de_tresse ~nb_trous (List.filteri (fun j _ -> j < k) tresse) in
          let non_reduit = Tresses.agit etat (List.nth tresse k) in
          verifie_etat (nom ^ " : agit") (etat_de (champ "agit" action)) non_reduit;
          verifie_etat (nom ^ " : reduit") (etat_de (champ "reduit" action)) (Tresses.normalise (Tresses.reduit non_reduit)))
        (J.to_list (champ "actions" cas)))
    (tresses ())

let test_dessin_etat () =
  List.iter
    (fun cas ->
      let tresse = tresse_de cas and taille = J.to_number (champ "taille" cas) in
      let etat = if tresse = [] then Tresses.etat_de_tresse ~nb_trous:5 [] else Tresses.etat_de_tresse tresse in
      let morceaux, trous, clou = Tresses.dessin_etat ~hauteur:taille ~largeur:taille etat in
      Array.iter2 (fun a b -> Alcotest.(check (float 1e-9)) "trou" 0. (norme (a -: b))) (points_de (champ "trous" cas)) trous;
      Alcotest.(check (float 1e-9)) "clou" 0. (norme (clou -: point_de (champ "clou" cas)));
      List.iter2
        (fun r p ->
          Alcotest.(check int) "nombre de points" (J.to_int (champ "n" r)) (Array.length p);
          let somme = Array.fold_left ( +: ) { x = 0.; y = 0. } p in
          Alcotest.(check (float 1e-6)) "somme" 0. (norme (somme -: point_de (champ "somme" r)));
          Array.iteri (fun j q -> Alcotest.(check (float 1e-9)) "échantillon" 0. (norme (q -: p.(25 * j)))) (points_de (champ "echantillon" r)))
        (J.to_list (champ "polylignes" cas)) (Tresses.polylignes morceaux))
    (J.to_list (champ "dessins" (Lazy.force meandre)))

(* Écart maximal entre deux familles de courbes ; échec si les arêtes traversées diffèrent. *)
let verifie_courbes nom tolerance attendu obtenu =
  let ecart a b =
    match (a, b) with
    | Sommet s, Sommet s' when s = s' -> 0.
    | Sur_arete (e, w), Sur_arete (e', w') when e = e' -> Float.abs (w -. w')
    | _ -> Alcotest.fail (nom ^ " : arêtes traversées différentes")
  in
  if List.length attendu <> List.length obtenu then Alcotest.fail (nom ^ " : nombre de courbes");
  let pire =
    List.fold_left2
      (fun m c c' ->
        if List.length c <> List.length c' then Alcotest.fail (nom ^ " : longueur d'une courbe");
        List.fold_left2 (fun m a b -> Float.max m (ecart a b)) m c c')
      0. attendu obtenu
  in
  if pire > tolerance then Alcotest.failf "%s : écart %g" nom pire

let test_courbes_avant_tension () =
  List.iter
    (fun cas ->
      let film = Film.cree ~tension:0 (tresse_de cas) in
      verifie_courbes "noeuds_de_polyligne" 1e-12 (courbes_de (champ "courbes" cas)) film.courbes)
    (J.to_list (champ "departs" (Lazy.force meandre)))

(* Le film construit en OCaml est l'état de départ du Python (reference_film.json). *)
let test_cree () =
  List.iter
    (fun f ->
      let fixe = champ "fixe" f and depart = List.hd (J.to_list (champ "etats" f)) in
      let film = Film.cree (tresse_de f) in
      let verifie_dispositions nom attendu obtenu =
        List.iter2
          (fun j (d : Film.disposition) ->
            Alcotest.(check (float 1e-12)) (nom ^ " : écart") (J.to_number (champ "ecart" j)) d.ecart;
            List.iter2 (fun a b -> Alcotest.(check (float 1e-9)) (nom ^ " : abscisse") a b) (reels (champ "abscisses" j)) (Array.to_list d.abscisses))
          (J.to_list attendu) (Array.to_list obtenu)
      in
      verifie_dispositions "dispositions" (champ "dispositions" fixe) film.dispositions;
      verifie_dispositions "milieux" (champ "milieux" fixe) film.milieux;
      Alcotest.(check (float 1e-12)) "decalage_bas" (J.to_number (champ "decalage_bas" fixe)) film.decalage_bas;
      Alcotest.(check (float 1e-12)) "y_axe" (J.to_number (champ "y_axe" fixe)) film.y_axe;
      (match J.to_list (champ "place_du_clou" fixe) with
       | [ j; x ] ->
         Alcotest.(check int) "place du clou" (J.to_int j) (fst film.place_du_clou);
         Alcotest.(check (float 1e-12)) "fraction du clou" (J.to_number x) (snd film.place_du_clou)
       | _ -> failwith "place_du_clou");
      Alcotest.(check (list int)) "trous" (entiers (champ "trous" depart)) (Array.to_list film.trous);
      Alcotest.(check (list (list int))) "triangles"
        (List.map entiers (J.to_list (champ "triangles" depart)))
        (List.sort compare (List.map (fun t -> let a, b, c = (t : Triangle.t :> int * int * int) in [ a; b; c ]) (Maillage.triangles film.maillage)));
      verifie_courbes "courbes tendues" 1e-12 (courbes_de (champ "courbes" depart)) film.courbes)
    (J.to_list (champ "films" (Lazy.force ref_film)))

(* Tout en OCaml, du mot de tresse au film : les mots relus après chaque lettre sont ceux de l'algèbre, et l'état
   final est celui du Python. *)
let test_film_complet () =
  List.iter
    (fun f ->
      let tresse = tresse_de f in
      let etats = Array.of_list (J.to_list (champ "etats" f)) in
      let film, _ =
        List.fold_left
          (fun (film, k) sigma ->
            let film, _ = Film.lettre film sigma in
            let algebre = Tresses.calcule_autofn_de_tresse ~nb_trous:film.nb_trous (List.filteri (fun j _ -> j <= k) tresse) in
            Alcotest.(check (list (list int))) "mots"
              (Array.to_list (Array.map (fun m -> Tresses.entiers_de_mot (m : Tresses.Reduit.t :> Tresses.mot_de_fn)) algebre))
              (List.map (fun m -> Tresses.entiers_de_mot (m : Tresses.Reduit.t :> Tresses.mot_de_fn)) (Film.mots film));
            (film, k + 1))
          (Film.cree tresse, 0) tresse
      in
      verifie_courbes "état final" 1e-9 (courbes_de (champ "courbes" etats.(Array.length etats - 1))) film.courbes)
    (J.to_list (champ "films" (Lazy.force ref_film)))

let () =
  Alcotest.run "meandre"
    [ ( "méandre",
        [ Alcotest.test_case "assert de tresses.py" `Quick test_intervalles_assert;
          Alcotest.test_case "intervalles et états" `Quick test_etats;
          Alcotest.test_case "agit et reduit" `Quick test_agit;
          Alcotest.test_case "dessin_etat" `Quick test_dessin_etat ] );
      ( "constructeur du film",
        [ Alcotest.test_case "courbes avant la tension" `Quick test_courbes_avant_tension;
          Alcotest.test_case "comme Film.__init__" `Quick test_cree;
          Alcotest.test_case "du mot au film" `Slow test_film_complet ] ) ]
