(* Le maillage à bord convexe. Voir raccord.mli. *)

open Geometrie
open Triangulation

let insere m p =
  let pos = m.Maillage.pos in
  let v = Array.length pos in
  let contient t =
    let a, b, c = (t : Triangle.t :> sommet * sommet * sommet) in
    let s = List.map (fun (x, y) -> croix (pos.(y) -: pos.(x)) (p -: pos.(x))) [ (a, b); (b, c); (c, a) ] in
    let echelle = List.fold_left Float.max 1. [ norme (pos.(b) -: pos.(a)); norme (pos.(c) -: pos.(b)) ] in
    let nuls = List.map (fun x -> Float.abs x < 1e-9 *. echelle) s in
    let tous signe = List.for_all2 (fun x nul -> signe x || nul) s nuls in
    if tous (fun x -> x > 0.) || tous (fun x -> x < 0.) then Some (a, b, c, nuls) else None
  in
  let triangles = Maillage.triangles m in
  match List.find_map (fun t -> Option.map (fun r -> (t, r)) (contient t)) triangles with
  | None -> invalid_arg "Raccord.insere : sommet hors du maillage"
  | Some (t, (a, b, c, nuls)) ->
    let retires, nouveaux =
      match List.find_index Fun.id nuls with
      | None -> ([ t ], [ Triangle.v a b v; Triangle.v b c v; Triangle.v c a v ])
      | Some j ->
        (* sur une arête : on coupe aussi le triangle voisin *)
        let x, y = List.nth [ (a, b); (b, c); (c, a) ] j in
        let cote = Arete.v x y in
        let autres = List.filter (fun u -> u <> t && List.mem cote (Triangle.aretes u)) triangles in
        let z = Triangle.oppose t cote in
        ( t :: autres,
          [ Triangle.v x z v; Triangle.v y z v ]
          @ List.concat_map (fun u -> let w = Triangle.oppose u cote in [ Triangle.v x w v; Triangle.v y w v ]) autres )
    in
    (* les orientations des triangles gardés n'ont pas changé (les sommets n'ont pas bougé) : les recalculer
       toutes revient au même *)
    let gardes = List.filter (fun u -> not (List.mem u retires)) triangles in
    (Maillage.cree (Array.append pos [| p |]) (gardes @ nouveaux), v)

let maillage_du_raccord ?(marge = 40.) ?(par_cote = 6) trous clou largeur hauteur =
  let x0 = -.marge and y0 = -.marge and x1 = largeur +. marge and y1 = hauteur +. marge in
  (* le bord tourne dans le sens horaire de l'écran ; bombé pour être strictement convexe *)
  let cote f = List.init par_cote (fun k -> let u = float k /. float par_cote in f u (3. *. Float.sin (Float.pi *. u))) in
  let bord =
    cote (fun u bosse -> { x = x0 +. (u *. (x1 -. x0)); y = y0 -. bosse })
    @ cote (fun u bosse -> { x = x1 +. bosse; y = y0 +. (u *. (y1 -. y0)) })
    @ cote (fun u bosse -> { x = x1 -. (u *. (x1 -. x0)); y = y1 +. bosse })
    @ cote (fun u bosse -> { x = x0 -. bosse; y = y1 -. (u *. (y1 -. y0)) })
  in
  let nb = List.length bord in
  (* éventail d'un polygone strictement convexe *)
  let m = Maillage.cree (Array.of_list bord) (List.init (nb - 2) (fun k -> Triangle.v 0 (k + 1) (k + 2))) in
  let trous = Array.of_list trous in
  let ordre = List.stable_sort (fun p q -> compare (trous.(p).x, trous.(p).y) (trous.(q).x, trous.(q).y))
      (List.init (Array.length trous) Fun.id) in
  let indices = Array.make (Array.length trous) 0 in
  let m = List.fold_left (fun m p -> let m, v = insere m trous.(p) in indices.(p) <- v; m) m ordre in
  let m, i_clou = match clou with None -> (m, None) | Some c -> let m, v = insere m c in (m, Some v) in
  let m, _ = Maillage.delaunay m [] in
  (m, Array.to_list indices, i_clou)
