(* Triangulation mobile. Voir triangulation.mli pour le rôle de chaque fonction. *)

open Geometrie

type point = Geometrie.point = { x : float; y : float }

let croix = Geometrie.croix

type sommet = int

module Arete = struct
  type t = sommet * sommet

  let v a b =
    if a = b then invalid_arg "Arete.v : une arête a deux sommets distincts";
    if a < b then (a, b) else (b, a)

  let compare = compare
end

module Triangle = struct
  type t = sommet * sommet * sommet

  let v a b c =
    match List.sort compare [ a; b; c ] with
    | [ a; b; c ] when a < b && b < c -> (a, b, c)
    | _ -> invalid_arg "Triangle.v : un triangle a trois sommets distincts"

  let compare = compare
  let aretes (a, b, c) = [ Arete.v a b; Arete.v a c; Arete.v b c ]

  let oppose (a, b, c) (u, v) =
    match List.filter (fun s -> s <> u && s <> v) [ a; b; c ] with
    | [ s ] -> s
    | _ -> invalid_arg "Triangle.oppose : l'arête n'est pas un côté du triangle"
end

module Triangles = Map.Make (Triangle)
module Aretes = Map.Make (Arete)

type noeud = Sommet of sommet | Sur_arete of Arete.t * float
type courbe = noeud list
type orientation = Direct | Indirect

module Maillage = struct
  type t = { pos : point array; signes : orientation Triangles.t }

  let signe_selon pos (a, b, c) = if croix (pos.(b) -: pos.(a)) (pos.(c) -: pos.(a)) > 0. then Direct else Indirect
  let signe m t = signe_selon m.pos t

  let cree pos triangles =
    let signes = List.fold_left (fun s t -> Triangles.add t (signe_selon pos t) s) Triangles.empty triangles in
    { pos; signes }

  (* Les orientations notées à la création restent : c'est ce qui permet à valide de voir un triangle retourné. *)
  let deplace m pos =
    if Array.length pos <> Array.length m.pos then invalid_arg "Maillage.deplace : nombre de sommets";
    { m with pos }

  let triangles m = List.map fst (Triangles.bindings m.signes)

  let aretes m =
    let ajoute t acc e = Aretes.update e (fun l -> Some (t :: Option.value l ~default:[])) acc in
    Triangles.fold (fun t _ acc -> List.fold_left (ajoute t) acc (Triangle.aretes t)) m.signes Aretes.empty

  let valide m = Triangles.for_all (fun t s -> signe m t = s) m.signes

  (* Les quatre virages a→b→c, b→c→d, c→d→a, d→a→b tournent tous dans le même sens, nettement. *)
  let convexe m a b c d =
    let p = m.pos in
    let virage x y z = croix (p.(y) -: p.(x)) (p.(z) -: p.(y)) in
    let s = [ virage a b c; virage b c d; virage c d a; virage d a b ] in
    List.for_all (fun x -> x > 1e-9) s || List.for_all (fun x -> x < -1e-9) s

  (* cot = cos / sin = (u·v) / |u × v| ; le dénominateur est borné pour les triangles plats. *)
  let cotangente m sommet x y =
    let u = m.pos.(x) -: m.pos.(sommet) and v = m.pos.(y) -: m.pos.(sommet) in
    scalaire u v /. Float.max (Float.abs (croix u v)) 1e-12

  (* Critère de Delaunay : l'arête ac est bonne si la somme des angles opposés (en b et en d) est au plus π,
     c'est-à-dire si cot b + cot d ≥ 0. Le Python recalcule toutes les arêtes pour tester si bd en est déjà une ;
     ici la table est calculée une fois. *)
  let cherche_arete_a_retourner m =
    let table = aretes m in
    Aretes.to_seq table
    |> Seq.find_map (fun ((a, c), tris) ->
           match tris with
           | [ t1; t2 ] ->
             let b = Triangle.oppose t1 (a, c) and d = Triangle.oppose t2 (a, c) in
             if cotangente m b a c +. cotangente m d a c >= -1e-9 then None
             else if not (convexe m a b c d) then None
             else if Aretes.mem (Arete.v b d) table then None
             else Some (a, b, c, d)
           | _ -> None (* arête du bord *))

  let position m = function
    | Sommet s -> m.pos.(s)
    | Sur_arete ((u, v), w) ->
      let pu = m.pos.(u) and pv = m.pos.(v) in
      { x = ((1. -. w) *. pu.x) +. (w *. pv.x); y = ((1. -. w) *. pu.y) +. (w *. pv.y) }

  (* Intersection de la corde [p, q] avec la droite (x, y) : p + t r = pos x + w s, on n'a besoin que de w. *)
  let coupe m u v b d =
    let p = position m u and q = position m v in
    let ((x, _) as e) = Arete.v b d in
    let y = snd e in
    let s = m.pos.(y) -: m.pos.(x) and r = q -: p in
    let w = croix (m.pos.(x) -: p) r /. croix r s in
    if not (w > -1e-6 && w < 1. +. 1e-6) then failwith "la corde ne coupe pas la nouvelle diagonale";
    Sur_arete (e, Float.min (Float.max w 1e-6) (1. -. 1e-6))

  (* De quel côté de la nouvelle diagonale bd est un noeud ? Le Python numérote les groupes 0, 1, 2 et None. *)
  type cote = Cote_a | Cote_c | Bout_de_bd | Ailleurs

  let courbe_apres_flip m courbe a b c d =
    let ac = Arete.v a c in
    let cote = function
      | Sommet s when s = a -> Cote_a
      | Sommet s when s = c -> Cote_c
      | Sommet s when s = b || s = d -> Bout_de_bd
      | Sommet _ -> Ailleurs
      | Sur_arete (e, _) when e = Arete.v a b || e = Arete.v d a -> Cote_a
      | Sur_arete (e, _) when e = Arete.v b c || e = Arete.v c d -> Cote_c
      | Sur_arete _ -> Ailleurs
    in
    let sans = List.filter (function Sur_arete (e, _) -> e <> ac | Sommet _ -> true) courbe in
    (* On recopie la courbe ; entre deux noeuds qui sont de part et d'autre de bd, on insère le point de bd. *)
    let rec recopie = function
      | u :: (v :: _ as reste) -> (
        match (cote u, cote v) with
        | Cote_a, Cote_c | Cote_c, Cote_a -> u :: coupe m u v b d :: recopie reste
        | _ -> u :: recopie reste)
      | fin -> fin
    in
    recopie sans

  let retourne m a b c d courbes =
    let signes =
      m.signes
      |> Triangles.remove (Triangle.v a b c)
      |> Triangles.remove (Triangle.v a c d)
      |> fun s ->
      List.fold_left
        (fun s t -> Triangles.add t (signe_selon m.pos t) s)
        s
        [ Triangle.v a b d; Triangle.v b c d ]
    in
    ({ m with signes }, List.map (fun courbe -> courbe_apres_flip m courbe a b c d) courbes)

  let delaunay m courbes =
    let rec boucle n m courbes =
      if n = 10_000 then failwith "les flips ne s'arrêtent pas";
      match cherche_arete_a_retourner m with
      | None -> (m, courbes)
      | Some (a, b, c, d) ->
        let m, courbes = retourne m a b c d courbes in
        boucle (n + 1) m courbes
    in
    boucle 0 m courbes
end

let decalage_axe = 0.01
let decalage_bord = 0.31

type maillage_initial = {
  maillage : Maillage.t;
  trous : sommet list;
  clou : sommet;
  haut : sommet list;
  bas : sommet list;
}

(* Échelle de triangles entre deux rangées triées par abscisse : on avance sur la rangée dont le point suivant
   est le plus à gauche, chaque pas donnant un triangle (deux points d'une rangée, un de l'autre). *)
let echelle x r1 r2 =
  let rec avance r1 r2 acc =
    match (r1, r2) with
    | i :: (i' :: _ as reste1), j :: j' :: _ when x i' <= x j' -> avance reste1 r2 (Triangle.v i i' j :: acc)
    | i :: _, j :: (j' :: _ as reste2) -> avance r1 reste2 (Triangle.v i j j' :: acc)
    | i :: (i' :: _ as reste1), [ j ] -> avance reste1 r2 (Triangle.v i i' j :: acc)
    | _ -> List.rev acc
  in
  avance r1 r2 []

let maillage_initial ?(decalage_bas = decalage_bord) trous clou _hauteur largeur =
  let y_axe = (List.hd trous).y +. decalage_axe in
  (* Les points sont numérotés dans l'ordre où on les ajoute, comme le ajoute du Python. *)
  let pts = ref [] and nb = ref 0 in
  let ajoute p =
    pts := p :: !pts;
    incr nb;
    !nb - 1
  in
  let rangee y xs = List.map (fun x -> ajoute { x; y }) xs in
  let avec_coins xs = (0. :: xs) @ [ largeur ] in
  let haut = rangee 3. (avec_coins (List.map (fun t -> t.x +. decalage_bord) trous)) in
  let axe = rangee y_axe (avec_coins (List.map (fun t -> t.x) trous)) in
  let nail = ajoute clou in
  let bas = rangee clou.y (avec_coins (List.map (fun t -> t.x +. decalage_bas) trous)) in
  let pos = Array.of_list (List.rev !pts) in
  let x i = pos.(i).x in
  let trie r = List.stable_sort (fun i j -> Float.compare (x i) (x j)) r in
  let triangles = echelle x (trie haut) (trie axe) @ echelle x (trie axe) (trie (bas @ [ nail ])) in
  let maillage, _ = Maillage.delaunay (Maillage.cree pos triangles) [] in
  let sans_bouts l = List.filteri (fun k _ -> k > 0 && k < List.length l - 1) l in
  { maillage; trous = sans_bouts axe; clou = nail; haut; bas }
