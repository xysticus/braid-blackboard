(* La détente du raccord (Detente), comparée au Python (reference_detente.json, écrit par genere_reference_detente.py) ; puis
   le film détendu de (σ₁σ₂⁻¹)³, vérifié (mots relus, croisements). *)

open Ardoise

module J = Yojson.Safe.Util

let point_de j = match J.to_list j with [ x; y ] -> { Geometrie.x = J.to_number x; y = J.to_number y } | _ -> failwith "point"

let ecart_max = ref 0.

let test_image image () =
  let lignes = List.map (fun l -> Array.of_list (List.map point_de (J.to_list l))) (J.to_list (J.member "lignes" image)) in
  let trous = Array.of_list (List.map point_de (J.to_list (J.member "trous" image))) in
  let clou = point_de (J.member "clou" image) and force = J.to_number (J.member "force" image) in
  let sortie = Detente.detend lignes trous clou force in
  let nom = Printf.sprintf "image %d" (J.to_int (J.member "numero" image)) in
  List.iter2
    (fun res p ->
      Alcotest.(check int) (nom ^ " : points du lacet") (J.to_int (J.member "n" res)) (Array.length p);
      let compare q r =
        let e = Geometrie.norme (Geometrie.( -: ) q r) in
        if e > !ecart_max then ecart_max := e;
        if e > 1e-6 then Alcotest.failf "%s : point à %g du Python" nom e
      in
      List.iteri (fun i q -> compare (point_de q) p.(25 * i)) (J.to_list (J.member "echantillon" res));
      compare (point_de (J.member "dernier" res)) p.(Array.length p - 1))
    (J.to_list (J.member "sortie" image)) sortie

let test_film () =
  let tresse = List.map Tresses.lettre_de_entier [ 1; -2; 1; -2; 1; -2 ] in
  let anomalies =
    Film_conforme.film ~verifie:true ~detente:true ~hauteur:800. ~largeur:800. ~marge:60. ~rendu:(fun _ -> ()) tresse
  in
  Alcotest.(check int) "anomalies du film détendu" 0 (List.length anomalies)

let () =
  let j = Yojson.Safe.from_file "reference_detente.json" in
  Alcotest.run "detente"
    [
      ( "detend",
        List.map (fun im -> Alcotest.test_case (Printf.sprintf "image %d" (J.to_int (J.member "numero" im))) `Quick (test_image im))
          (J.to_list (J.member "images" j)) );
      ("film", [ Alcotest.test_case "(σ1σ2⁻¹)³" `Slow test_film ]);
    ]
