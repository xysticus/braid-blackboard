(* Tests de l'étape 7a : la carte de Schwarz–Christoffel, comparée au Python (reference_conforme.json, écrit par
   genere_reference_conforme.py). Les tolérances tiennent compte des arrondis de la puissance complexe et de la
   méthode de Newton, qui peuvent différer de numpy au dernier chiffre. *)

open Ardoise
module J = Yojson.Safe.Util

let reference = lazy (Yojson.Safe.from_file "reference_conforme.json")
let reels j = List.map J.to_number (J.to_list j)
let complexe j = match reels j with [ re; im ] -> { Complex.re; im } | _ -> failwith "complexe"

let proches nom tolerance a b =
  if Float.abs (a -. b) > tolerance then Alcotest.failf "%s : %.17g au lieu de %.17g" nom b a

let proches_c nom tolerance (a : Complex.t) (b : Complex.t) =
  if Complex.norm (Complex.sub a b) > tolerance then
    Alcotest.failf "%s : (%.12g, %.12g) au lieu de (%.12g, %.12g)" nom b.re b.im a.re a.im

let cartes () = J.to_list (J.member "cartes" (Lazy.force reference))

let test_carte k j () =
  let nom = Printf.sprintf "carte %d" k in
  let sommets = Array.of_list (List.map complexe (J.to_list (J.member "sommets" j))) in
  let carte = Conforme.cree sommets in
  List.iteri (fun i b -> proches (nom ^ " : beta") 1e-12 b carte.Conforme.beta.(i)) (reels (J.member "beta" j));
  List.iteri (fun i e -> proches (nom ^ " : écarts") (1e-9 *. e) e carte.ecarts.(i)) (reels (J.member "ecarts" j));
  List.iteri (fun i w -> proches (nom ^ " : w") 1e-7 w carte.w.(i)) (reels (J.member "w" j));
  proches (nom ^ " : delta") 1e-7 (J.to_number (J.member "delta" j)) carte.delta;
  List.iter
    (fun b -> match J.to_list b with [ t; z ] -> proches_c (nom ^ " : bord") 1e-6 (complexe z) (Conforme.bord carte (J.to_number t)) | _ -> ())
    (J.to_list (J.member "bords" j));
  List.iter
    (fun a ->
      match J.to_list a with
      | [ p; l; t ] -> proches (nom ^ " : antécédent du bord") 1e-6 (J.to_number t) (Conforme.antecedent_bord carte (J.to_int p) (J.to_number l))
      | _ -> ())
    (J.to_list (J.member "antecedents_bord" j));
  List.iter
    (fun a -> match J.to_list a with [ w; z ] -> proches_c (nom ^ " : image") 1e-6 (complexe z) (Conforme.image carte (complexe w)) | _ -> ())
    (J.to_list (J.member "images" j));
  (* Newton s'arrête dès que l'image est à 1e-4 près : on compare les antécédents à 1e-3 près *)
  List.iter
    (fun a -> match J.to_list a with [ z; w ] -> proches_c (nom ^ " : antécédent") 1e-3 (complexe w) (Conforme.antecedent carte (complexe z)) | _ -> ())
    (J.to_list (J.member "antecedents" j));
  match J.to_list (J.member "demi_cercle" j) with
  | [ w0; w1; arc ] ->
      let dc = Conforme.demi_cercle (J.to_number w0) (J.to_number w1) in
      let z0 = Conforme.bord carte dc.(0).re and z1 = Conforme.bord carte dc.(Array.length dc - 1).re in
      let obtenu = Conforme.chemin ~z1 carte dc z0 in
      let attendu = List.map complexe (J.to_list arc) in
      Alcotest.(check int) (nom ^ " : points du demi-cercle") (List.length attendu) (Array.length obtenu);
      List.iteri (fun i z -> proches_c (nom ^ " : demi-cercle") 1e-6 z obtenu.(i)) attendu
  | _ -> ()

(* 7b : la lettre *)

let point_de j = match reels j with [ x; y ] -> { Geometrie.x; y } | _ -> failwith "point"

let proches_p nom tolerance (a : Geometrie.point) (b : Geometrie.point) =
  if Float.hypot (a.x -. b.x) (a.y -. b.y) > tolerance then
    Alcotest.failf "%s : (%.12g, %.12g) au lieu de (%.12g, %.12g)" nom b.x b.y a.x a.y

let lettres () = J.to_list (J.member "lettres" (Lazy.force reference))

let test_lettre j () =
  let entiers = List.map J.to_int (J.to_list (J.member "tresse" j)) in
  let k = J.to_int (J.member "k" j) and s = J.to_number (J.member "s" j) and e = J.to_int (J.member "e" j) in
  let nom = Printf.sprintf "lettre %d, s = %g" k s in
  let tresse = Tresses.tresse_de_entiers entiers in
  let nb_trous = List.fold_left (fun a x -> max a (abs x)) 0 entiers + 1 in
  let prefixe n = List.filteri (fun i _ -> i < n) tresse in
  let cle = Tresses.etat_de_tresse ~nb_trous (prefixe k) and suivante = Tresses.etat_de_tresse ~nb_trous (prefixe (k + 1)) in
  let l = Conforme.lettre ~hauteur:680. ~largeur:680. cle suivante (List.nth tresse k) in
  let v = Conforme.ligne l e s in
  List.iteri (fun i z -> proches_c (nom ^ " : ligne") 1e-9 (complexe z) v.(i)) (J.to_list (J.member "ligne" j));
  List.iteri
    (fun lacet pieds ->
      let xs = List.nth l.etats.(e).Tresses.lacets lacet in
      List.iteri
        (fun q p ->
          match J.to_list p with
          | [ morceau; longueur; position ] ->
              let obtenu = Conforme.pied l e xs.(q) s v in
              Alcotest.(check int) (nom ^ " : morceau du pied") (J.to_int morceau) obtenu.morceau;
              proches (nom ^ " : longueur du pied") 1e-9 (J.to_number longueur) obtenu.longueur;
              proches_c (nom ^ " : position du pied") 1e-9 (complexe position) obtenu.position
          | _ -> failwith "pied")
        (J.to_list pieds))
    (J.to_list (J.member "pieds" j));
  proches (nom ^ " : aplatissement") 1e-12 (J.to_number (J.member "aplati" j)) (Conforme.aplati l ~reduction:1. s);
  let dessin = Conforme.dessin l ~reduction:1. e s in
  let attendu = J.to_list (J.member "dessin" j) in
  Alcotest.(check int) (nom ^ " : nombre de lacets") (List.length attendu) (List.length dessin);
  List.iter2
    (fun r p ->
      Alcotest.(check int) (nom ^ " : points du lacet") (J.to_int (J.member "n" r)) (Array.length p);
      List.iteri (fun i q -> proches_p (nom ^ " : point du lacet") 1e-8 (point_de q) p.(25 * i)) (J.to_list (J.member "echantillon" r));
      proches_p (nom ^ " : dernier point") 1e-8 (point_de (J.member "dernier" r)) p.(Array.length p - 1);
      let somme = Array.fold_left (fun (a : Geometrie.point) (b : Geometrie.point) -> { Geometrie.x = a.x +. b.x; y = a.y +. b.y }) { x = 0.; y = 0. } p in
      proches_p (nom ^ " : somme des points") 1e-5 (point_de (J.member "somme" r)) somme)
    attendu dessin;
  List.iteri (fun i q -> proches_p (nom ^ " : trou") 1e-9 (point_de q) (Conforme.trous_ecran l ~reduction:1. s).(i)) (J.to_list (J.member "trous" j))

(* 7c : le raccord par triangulation, reconstruit à partir des entrées capturées dans le film Python *)

let raccords () = J.to_list (J.member "raccords" (Lazy.force reference))
let lignes_de j = List.map (fun l -> Array.of_list (List.map point_de (J.to_list l))) (J.to_list j)

let test_raccord j () =
  let entiers = List.map J.to_int (J.to_list (J.member "tresse" j)) in
  let k = J.to_int (J.member "k" j) in
  let nom = Printf.sprintf "raccord de la lettre %d" k in
  let tresse = Tresses.tresse_de_entiers entiers in
  let nb_trous = List.fold_left (fun a x -> max a (abs x)) 0 entiers + 1 in
  let prefixe n = List.filteri (fun i _ -> i < n) tresse in
  let cle = Tresses.etat_de_tresse ~nb_trous (prefixe k) and suivante = Tresses.etat_de_tresse ~nb_trous (prefixe (k + 1)) in
  let largeur = J.to_number (J.member "largeur" j) and hauteur = J.to_number (J.member "hauteur" j) in
  let l = Conforme.lettre ~hauteur ~largeur cle suivante (List.nth tresse k) in
  let nombre n = J.to_number (J.member n j) in
  let r =
    Raccord.raccord ~positions:(fun s reduction -> Conforme.trous_ecran l ~reduction s) ~clou:(point_de (J.member "clou" j))
      ~largeur ~hauteur ~s_a:(nombre "s_a") ~r_a:(nombre "r_a") ~depart:(lignes_de (J.member "depart" j)) ~s_b:(nombre "s_b")
      ~r_b:(nombre "r_b") ~arrivee:(lignes_de (J.member "arrivee" j)) ~temps:(Array.of_list (reels (J.member "temps" j)))
      ~tournants:(List.map J.to_int (J.to_list (J.member "tournants" j))) ()
  in
  List.iter
    (fun image ->
      let f = J.to_int (J.member "f" image) and poids = J.to_number (J.member "poids" image) in
      let nom = Printf.sprintf "%s, image %d" nom f in
      let lignes, anomalies = Raccord.lignes r f poids in
      Alcotest.(check int) (nom ^ " : anomalies") (J.to_int (J.member "anomalies" image)) (List.length anomalies);
      List.iter2
        (fun res p ->
          Alcotest.(check int) (nom ^ " : points du lacet") (J.to_int (J.member "n" res)) (Array.length p);
          List.iteri (fun i q -> proches_p (nom ^ " : point du lacet") 1e-6 (point_de q) p.(25 * i)) (J.to_list (J.member "echantillon" res));
          proches_p (nom ^ " : dernier point") 1e-6 (point_de (J.member "dernier" res)) p.(Array.length p - 1))
        (J.to_list (J.member "lignes" image)) lignes)
    (J.to_list (J.member "images" j))

let () =
  Alcotest.run "conforme"
    [
      ("carte", List.mapi (fun k j -> Alcotest.test_case (Printf.sprintf "carte %d" k) `Quick (test_carte k j)) (cartes ()));
      ("lettre", List.mapi (fun k j -> Alcotest.test_case (Printf.sprintf "lettre %d" k) `Quick (test_lettre j)) (lettres ()));
      ("raccord", List.mapi (fun k j -> Alcotest.test_case (Printf.sprintf "raccord %d" k) `Quick (test_raccord j)) (raccords ()));
    ]
