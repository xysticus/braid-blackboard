(* Tests de l'étape 2 : maillage de départ, critère de Delaunay, flips et courbes, comparés au Python
   (reference_triangulation.json, écrit par genere_reference_triangulation.py). *)

open Ardoise.Triangulation
module J = Yojson.Safe.Util

let reference = lazy (Yojson.Safe.from_file "reference_triangulation.json")
let entiers j = List.map J.to_int (J.to_list j)
let reel = J.to_number
let point_de j = match J.to_list j with [ x; y ] -> { x = reel x; y = reel y } | _ -> failwith "point"

let noeud_de j =
  match J.to_list j with
  | [ s ] -> Sommet (J.to_int s)
  | [ u; v; w ] -> Sur_arete (Arete.v (J.to_int u) (J.to_int v), reel w)
  | _ -> failwith "noeud"

let courbe_de j = List.map noeud_de (J.to_list j)
let triangles_de j = List.map (fun t -> match entiers t with [ a; b; c ] -> Triangle.v a b c | _ -> failwith "triangle") (J.to_list j)
let entiers_de_triangle (t : Triangle.t) = let a, b, c = (t :> int * int * int) in [ a; b; c ]

(* Les triangles d'un maillage, en listes d'entiers triées : la forme du JSON. *)
let liste_triangles m = List.sort compare (List.map entiers_de_triangle (Maillage.triangles m))

(* Égalité de deux courbes, à 1e-9 près sur les fractions. *)
let noeud_proche a b =
  match (a, b) with
  | Sommet s, Sommet s' -> s = s'
  | Sur_arete (e, w), Sur_arete (e', w') -> e = e' && Float.abs (w -. w') < 1e-9
  | _ -> false

let courbe = Alcotest.testable (fun f c -> Format.fprintf f "<courbe de %d noeuds>" (List.length c))
    (fun a b -> List.length a = List.length b && List.for_all2 noeud_proche a b)

let tri_entiers = Alcotest.(list (list int))

let cas_delaunay () = J.to_list (J.member "delaunay" (Lazy.force reference))

let maillage_du_cas cas =
  let trous = List.map point_de (J.to_list (J.member "trous" cas)) in
  maillage_initial ~decalage_bas:(reel (J.member "decalage_bas" cas)) trous
    (point_de (J.member "clou" cas)) 800. 800.

let test_maillage_initial () =
  List.iteri
    (fun k cas ->
      let mi = maillage_du_cas cas in
      let nom = Printf.sprintf "cas %d" k in
      Alcotest.check tri_entiers (nom ^ " : triangles")
        (List.map entiers (J.to_list (J.member "triangles" cas)))
        (liste_triangles mi.maillage);
      Alcotest.(check (list int)) (nom ^ " : trous") (entiers (J.member "indices_trous" cas)) mi.trous;
      Alcotest.(check int) (nom ^ " : clou") (J.to_int (J.member "clou_indice" cas)) mi.clou;
      Alcotest.(check (list int)) (nom ^ " : haut") (entiers (J.member "haut" cas)) mi.haut;
      Alcotest.(check (list int)) (nom ^ " : bas") (entiers (J.member "bas" cas)) mi.bas)
    (cas_delaunay ())

(* Après delaunay : plus d'arête à retourner, et aucun triangle retourné. *)
let test_delaunay_stable () =
  List.iter
    (fun cas ->
      let m = (maillage_du_cas cas).maillage in
      Alcotest.(check bool) "valide" true (Maillage.valide m);
      Alcotest.(check bool) "plus rien à retourner" true (Maillage.cherche_arete_a_retourner m = None))
    (cas_delaunay ())

let etats () = J.to_list (J.member "flips" (Lazy.force reference))

let test_courbe_apres_flip () =
  let n = ref 0 in
  List.iteri
    (fun i etat ->
      let pos = Array.of_list (List.map point_de (J.to_list (J.member "pos" etat))) in
      let m = Maillage.cree pos (triangles_de (J.member "triangles" etat)) in
      let courbes = List.map courbe_de (J.to_list (J.member "courbes" etat)) in
      List.iter
        (fun flip ->
          let a, b, c, d =
            match entiers (J.member "quad" flip) with [ a; b; c; d ] -> (a, b, c, d) | _ -> failwith "quad"
          in
          let apres = J.member "courbes_apres" flip in
          List.iteri
            (fun k avant ->
              let attendu =
                match J.member (string_of_int k) apres with `Null -> avant | j -> courbe_de j
              in
              incr n;
              Alcotest.check courbe
                (Printf.sprintf "état %d, flip (%d %d %d %d), courbe %d" i a b c d k)
                attendu
                (Maillage.courbe_apres_flip m avant a b c d))
            courbes)
        (J.to_list (J.member "flips" etat)))
    (etats ());
  Printf.printf "%d courbes comparées au Python\n" !n

(* Un flip suivi du flip inverse rend les mêmes triangles. *)
let test_aller_retour () =
  List.iter
    (fun etat ->
      let pos = Array.of_list (List.map point_de (J.to_list (J.member "pos" etat))) in
      let m = Maillage.cree pos (triangles_de (J.member "triangles" etat)) in
      List.iter
        (fun flip ->
          match entiers (J.member "quad" flip) with
          | [ a; b; c; d ] ->
            let m1, _ = Maillage.retourne m a b c d [] in
            let m2, _ = Maillage.retourne m1 b c d a [] in
            Alcotest.check tri_entiers "aller-retour" (liste_triangles m) (liste_triangles m2)
          | _ -> failwith "quad")
        (J.to_list (J.member "flips" etat)))
    (etats ())

let () =
  Alcotest.run "triangulation"
    [ ( "maillage de départ",
        [ Alcotest.test_case "comme le Python" `Quick test_maillage_initial;
          Alcotest.test_case "Delaunay stable" `Quick test_delaunay_stable ] );
      ( "flips",
        [ Alcotest.test_case "courbe_apres_flip comme le Python" `Quick test_courbe_apres_flip;
          Alcotest.test_case "aller-retour" `Quick test_aller_retour ] ) ]
