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

let () =
  Alcotest.run "conforme"
    [ ("carte", List.mapi (fun k j -> Alcotest.test_case (Printf.sprintf "carte %d" k) `Quick (test_carte k j)) (cartes ())) ]
