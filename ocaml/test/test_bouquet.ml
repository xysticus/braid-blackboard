(* Tests de l'étape 8 : le premier bouquet (lib/bouquet.ml), comparé au Python (reference_bouquet.json, écrit par
   genere_reference_bouquet.py). Les plantes : centre, phases, positions des trous, direction de la tige, à 1e-9 près.
   Le film : l'état de la triangulation après les images 0, 1, 10, 40, 80, 120 et 169 (positions des trous, polylignes des
   35 lacets). *)

open Ardoise
module J = Yojson.Safe.Util

let reference = lazy (Yojson.Safe.from_file "reference_bouquet.json")
let reels j = List.map J.to_number (J.to_list j)
let point_de j = match reels j with [ x; y ] -> { Geometrie.x; y } | _ -> failwith "point"

let proche nom tolerance a b = if Float.abs (a -. b) > tolerance then Alcotest.failf "%s : %.17g au lieu de %.17g" nom b a

let proche_p nom tolerance (a : Geometrie.point) (b : Geometrie.point) =
  if Float.hypot (a.x -. b.x) (a.y -. b.y) > tolerance then
    Alcotest.failf "%s : (%.12g, %.12g) au lieu de (%.12g, %.12g)" nom b.x b.y a.x a.y

(* la graine et la tresse de départ ne dépendent pas du temps : un seul état pour toutes les plantes *)
let depart = lazy (Bouquet.cree Bouquet.bouquet)

let test_plante j () =
  let p = Lazy.force depart in
  let n = J.to_int (J.member "n" j) and t = J.to_number (J.member "t" j) in
  let nom = Printf.sprintf "plante %d, t = %g" n t in
  proche_p (nom ^ " : centre") 1e-9 (point_de (J.member "centre" j)) (Bouquet.centre p n t);
  (match reels (J.member "phases" j) with
  | [ m; b; e ] ->
      let m', b', e' = Bouquet.phases p.groupes.(n) t in
      proche (nom ^ " : montée") 1e-12 m m';
      proche (nom ^ " : bourgeon") 1e-12 b b';
      proche (nom ^ " : éclosion") 1e-12 e e'
  | _ -> failwith "phases");
  let trous =
    match p.groupes.(n) with Bouquet.Feuille _ -> Bouquet.trous_de_feuille p n t | Bouquet.Fleur _ -> Bouquet.trous_de_fleur p n t
  in
  let attendu = List.map point_de (J.to_list (J.member "trous" j)) in
  Alcotest.(check int) (nom ^ " : nombre de trous") (List.length attendu) (Array.length trous);
  List.iteri (fun k q -> proche_p (nom ^ " : trou") 1e-9 q trous.(k)) attendu;
  proche_p (nom ^ " : tige") 1e-12 (point_de (J.member "tige" j)) (Bouquet.direction_de_tige p n)

(* Le film : on rejoue la boucle de film_bouquet (images à 0,08 s) et l'on compare aux images demandées. *)
let test_film () =
  let attendues = J.to_list (J.member "images" (Lazy.force reference)) in
  let dernier = List.fold_left (fun a j -> max a (J.to_int (J.member "n" j))) 0 attendues in
  let rec boucle n p = function
    | [] -> ()
    | j :: reste ->
        let numero = J.to_int (J.member "n" j) in
        if n > dernier then ()
        else begin
          let p =
            if n = 0 then p else Bouquet.deplace p (Bouquet.choregraphie p (float n *. 0.08)) (2. *. p.e)
          in
          if n = numero then begin
            let nom = Printf.sprintf "image %d" n in
            let positions = Bouquet.positions p in
            List.iteri (fun k q -> proche_p (nom ^ " : trou") 1e-6 (point_de q) positions.(k)) (J.to_list (J.member "positions" j));
            let lignes = Bouquet.polylignes p in
            Alcotest.(check int) (nom ^ " : nombre de lacets") (List.length (J.to_list (J.member "lignes" j))) (List.length lignes);
            List.iteri
              (fun l (r, pl) ->
                let nom = Printf.sprintf "%s, lacet %d" nom l in
                Alcotest.(check int) (nom ^ " : points") (J.to_int (J.member "n" r)) (Array.length pl);
                List.iteri (fun i q -> proche_p (nom ^ " : point") 1e-6 (point_de q) pl.(25 * i)) (J.to_list (J.member "echantillon" r));
                proche_p (nom ^ " : dernier point") 1e-6 (point_de (J.member "dernier" r)) pl.(Array.length pl - 1))
              (List.combine (J.to_list (J.member "lignes" j)) lignes);
            boucle (n + 1) p reste
          end
          else boucle (n + 1) p (j :: reste)
        end
  in
  boucle 0 (Lazy.force depart) attendues

let () =
  Alcotest.run "bouquet"
    [
      ("plantes", List.mapi (fun k j -> Alcotest.test_case (Printf.sprintf "plante %d" k) `Quick (test_plante j)) (J.to_list (J.member "plantes" (Lazy.force reference))));
      ("film", [ Alcotest.test_case "169 images" `Slow test_film ]);
    ]
