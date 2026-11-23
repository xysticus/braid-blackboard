(* Le film conforme de python/Conforme.py : étape 7 du plan OCaml (voir plan_ocaml.md).
   7a : la carte de Schwarz–Christoffel (classe Carte du Python) et les demi-cercles du demi-plan. *)

(* --- outils numériques (les fonctions numpy utilisées par Carte) --- *)

(* np.linspace(debut, fin, n) : même calcul que numpy (pas multiplié par l'indice, dernier point exact). *)
let linspace debut fin n =
  if n = 1 then [| debut |]
  else
    let pas = (fin -. debut) /. float_of_int (n - 1) in
    Array.init n (fun k -> if k = n - 1 then fin else (float_of_int k *. pas) +. debut)

(* np.interp(x, xp, fp), xp croissant : interpolation linéaire, valeurs extrêmes au-delà des bouts. *)
let interp x xp fp =
  let n = Array.length xp in
  if x <= xp.(0) then fp.(0)
  else if x >= xp.(n - 1) then fp.(n - 1)
  else begin
    (* le plus grand j tel que xp.(j) <= x, par dichotomie *)
    let bas = ref 0 and haut = ref (n - 1) in
    while !haut - !bas > 1 do
      let milieu = (!bas + !haut) / 2 in
      if xp.(milieu) <= x then bas := milieu else haut := milieu
    done;
    let j = !bas in
    let pente = (fp.(j + 1) -. fp.(j)) /. (xp.(j + 1) -. xp.(j)) in
    (pente *. (x -. xp.(j))) +. fp.(j)
  end

(* La table cumulée [0; c0; c0 + c1; ...] (le np.concatenate(([0], np.cumsum(...))) du Python). *)
let cumul_depuis_zero valeurs =
  let n = Array.length valeurs in
  let r = Array.make (n + 1) 0. in
  for k = 0 to n - 1 do
    r.(k + 1) <- r.(k) +. valeurs.(k)
  done;
  r

(* Résolution de J x = F par l'élimination de Gauss avec pivot partiel (np.linalg.solve ; LAPACK fait de même, aux
   arrondis près). *)
let resous j f =
  let n = Array.length f in
  let a = Array.map Array.copy j and b = Array.copy f in
  for colonne = 0 to n - 1 do
    let pivot = ref colonne in
    for ligne = colonne + 1 to n - 1 do
      if Float.abs a.(ligne).(colonne) > Float.abs a.(!pivot).(colonne) then pivot := ligne
    done;
    let t = a.(colonne) in
    a.(colonne) <- a.(!pivot);
    a.(!pivot) <- t;
    let t = b.(colonne) in
    b.(colonne) <- b.(!pivot);
    b.(!pivot) <- t;
    for ligne = colonne + 1 to n - 1 do
      let facteur = a.(ligne).(colonne) /. a.(colonne).(colonne) in
      for k = colonne to n - 1 do
        a.(ligne).(k) <- a.(ligne).(k) -. (facteur *. a.(colonne).(k))
      done;
      b.(ligne) <- b.(ligne) -. (facteur *. b.(colonne))
    done
  done;
  let x = Array.make n 0. in
  for ligne = n - 1 downto 0 do
    let s = ref b.(ligne) in
    for k = ligne + 1 to n - 1 do
      s := !s -. (a.(ligne).(k) *. x.(k))
    done;
    x.(ligne) <- !s /. a.(ligne).(ligne)
  done;
  x

(* Module d'un complexe, comme np.abs : hypot (module_c calcule autrement, et diffère parfois au dernier
   chiffre). *)
let module_c (z : Complex.t) = Float.hypot z.re z.im

(* --- la carte de Schwarz–Christoffel --- *)

type table = { t : float array; l : float array }
(* Une table du bord : des antécédents réels t et la longueur l parcourue sur le bord depuis le début du morceau. *)

type carte = {
  sommets : Complex.t array;  (** V_0 ... V_(m-1) *)
  longueurs : float array;  (** des segments V_(k-1) V_k *)
  directions : Complex.t array;  (** directions unitaires des segments *)
  beta : float array;  (** β_k : -angle dont tourne le bord en V_k / π *)
  ecarts : float array;  (** w_(k+1) - w_k *)
  w : float array;  (** antécédents des sommets, w_0 = 0 *)
  tables : table array;  (** morceaux du bord : 0 demi-droite de gauche, 1 .. m-1 segments, m demi-droite de droite *)
  delta : float;  (** z ≈ w + delta loin à droite *)
}

let n_table = 300 (* points des tables du bord par demi-morceau *)
let loin = 4000. (* longueur des tables des deux demi-droites, en pixels *)

(* |dz/dw| aux points réels t, sans le facteur du sommet d'indice sauf. *)
let module_sans beta w t sauf =
  Array.map
    (fun ti ->
      let r = ref 1. in
      Array.iteri (fun j wj -> if j <> sauf then r := !r *. (Float.abs (ti -. wj) ** beta.(j))) w;
      !r)
    t

(* Table du bord à partir de l'antécédent w_k, dans le sens donné (+1 ou -1), sur la distance d, avec n points :
   le changement de variable t = w_k + sens d s^q, q = 1 / (1 + β_k), enlève la singularité en w_k ; la longueur
   cumulée est l'intégrale de |dz/dw| par la méthode des trapèzes en s. *)
let depuis beta w k sens d n =
  let q = 1. /. (1. +. beta.(k)) in
  let s = linspace 0. 1. n in
  let t = Array.map (fun si -> w.(k) +. (sens *. d *. (si ** q))) s in
  let facteur = q *. (d ** (1. +. beta.(k))) in
  let g = Array.map (fun m -> facteur *. m) (module_sans beta w t k) in
  let pas = Array.init (n - 1) (fun i -> (g.(i + 1) +. g.(i)) /. 2. *. (s.(i + 1) -. s.(i))) in
  { t; l = cumul_depuis_zero pas }

(* Longueurs des segments données par des écarts entre antécédents (chaque segment intégré par ses deux moitiés,
   depuis chacune de ses extrémités). *)
let cotes beta ecarts n =
  let w = cumul_depuis_zero ecarts in
  Array.mapi
    (fun k e ->
      let dernier tb = tb.l.(Array.length tb.l - 1) in
      dernier (depuis beta w k 1. (e /. 2.) n) +. dernier (depuis beta w (k + 1) (-1.) (e /. 2.) n))
    ecarts

let dernier a = a.(Array.length a - 1)

let tables_du_bord beta w ecarts longueurs =
  let m = Array.length w in
  let gauche = depuis beta w 0 (-1.) loin (2 * n_table) in
  let segments =
    Array.init (m - 1) (fun i ->
        let p = i + 1 in
        let t1 = depuis beta w (p - 1) 1. (ecarts.(p - 1) /. 2.) n_table in
        let t2 = depuis beta w p (-1.) (ecarts.(p - 1) /. 2.) n_table in
        let total = dernier t1.l +. dernier t2.l in
        let n2 = Array.length t2.t in
        (* la seconde moitié, parcourue à l'envers et sans son premier point (le milieu, déjà dans la première) *)
        let t = Array.append t1.t (Array.init (n2 - 1) (fun j -> t2.t.(n2 - 2 - j))) in
        let l = Array.append t1.l (Array.init (n2 - 1) (fun j -> total -. t2.l.(n2 - 2 - j))) in
        { t; l = Array.map (fun x -> x *. longueurs.(p - 1) /. total) l })
  in
  let droite = depuis beta w (m - 1) 1. loin (2 * n_table) in
  Array.concat [ [| gauche |]; segments; [| droite |] ]

exception Pas_de_convergence of string

(* La carte du demi-plan supérieur (w) sur la région au-dessus de la ligne brisée de sommets V_0 ... V_(m-1) (y vers
   le haut, V_0 et V_(m-1) à la même hauteur, demi-droites horizontales au-delà). ecarts : écarts de départ de la
   méthode de Newton (par défaut, les longueurs des segments). *)
let cree ?ecarts sommets =
  let m = Array.length sommets in
  let cotes_c = Array.init (m - 1) (fun k -> Complex.sub sommets.(k + 1) sommets.(k)) in
  let longueurs = Array.map module_c cotes_c in
  let directions = Array.mapi (fun k c -> Complex.div c { re = longueurs.(k); im = 0. }) cotes_c in
  let d = Array.concat [ [| Complex.one |]; directions; [| Complex.one |] ] in
  let beta = Array.init m (fun k -> -.Complex.arg (Complex.div d.(k + 1) d.(k)) /. Float.pi) in
  (* antécédents des sommets : on cherche les écarts w_(k+1) - w_k qui donnent les longueurs des segments ; Newton
     sur leurs logarithmes, jacobienne par différences finies, pas borné à 1 *)
  let x = ref (Array.map log (match ecarts with None -> longueurs | Some e -> e)) in
  let ecart_relatif e = Array.mapi (fun k c -> (c /. longueurs.(k)) -. 1.) (cotes beta (Array.map exp e) 120) in
  let rec newton iteration =
    if iteration = 80 then raise (Pas_de_convergence "Schwarz–Christoffel : les antécédents des sommets ne convergent pas");
    let f = ecart_relatif !x in
    if Array.fold_left (fun a v -> Float.max a (Float.abs v)) 0. f >= 1e-11 then begin
      let n = Array.length !x in
      let jac = Array.make_matrix n n 0. in
      for k = 0 to n - 1 do
        let y = Array.copy !x in
        y.(k) <- y.(k) +. 1e-7;
        let fy = ecart_relatif y in
        for i = 0 to n - 1 do
          jac.(i).(k) <- (fy.(i) -. f.(i)) /. 1e-7
        done
      done;
      let pas = resous jac f in
      x := Array.mapi (fun k v -> v -. Float.min 1. (Float.max (-1.) pas.(k))) !x;
      newton (iteration + 1)
    end
  in
  newton 0;
  let ecarts = Array.map exp !x in
  let w = cumul_depuis_zero ecarts in
  let tables = tables_du_bord beta w ecarts longueurs in
  let droite = tables.(m) in
  let delta = sommets.(m - 1).re +. dernier droite.l -. dernier droite.t in
  { sommets; longueurs; directions; beta; ecarts; w; tables; delta }

(* Antécédent (réel) du point du bord à la longueur donnée sur le morceau. *)
let antecedent_bord carte morceau longueur =
  let tb = carte.tables.(morceau) in
  if longueur < 0. || longueur > dernier tb.l then invalid_arg "antecedent_bord : point hors des tables du bord";
  interp longueur tb.l tb.t

let renverse a = Array.init (Array.length a) (fun i -> a.(Array.length a - 1 - i))

(* Point du bord image du réel t. *)
let bord carte t =
  let w = carte.w and m = Array.length carte.sommets in
  let reel x = { Complex.re = x; im = 0. } in
  if t <= w.(0) then
    let tb = carte.tables.(0) in
    Complex.sub carte.sommets.(0) (reel (interp t (renverse tb.t) (renverse tb.l)))
  else if t >= dernier w then
    let tb = carte.tables.(m) in
    Complex.add carte.sommets.(m - 1) (reel (interp t tb.t tb.l))
  else
    (* np.searchsorted(w, t) : le premier p tel que w_p >= t *)
    let p = ref 0 in
    while w.(!p) < t do
      incr p
    done;
    let tb = carte.tables.(!p) in
    Complex.add carte.sommets.(!p - 1) (Complex.mul (reel (interp t tb.t tb.l)) carte.directions.(!p - 1))

(* dz/dw = Π (w - w_k)^β_k. La partie imaginaire est ramenée à 0 si elle est négative ; 0. +. 0. évite le -0. (l'argument
   d'un réel négatif doit être π, pas -π). *)
let derivee carte (w : Complex.t) =
  let w = { w with im = Float.max w.im 0. +. 0. } in
  let r = ref Complex.one in
  Array.iteri
    (fun k wk -> r := Complex.mul !r (Complex.pow (Complex.sub w { re = wk; im = 0. }) { re = carte.beta.(k); im = 0. }))
    carte.w;
  !r

(* Images des points ws (un chemin du demi-plan) en intégrant dz/dw depuis z0, image de ws.(0) (méthode du point
   milieu) ; si l'on connaît z1, image du dernier point, l'erreur d'intégration est répartie le long du chemin, au
   prorata de la longueur parcourue. Les points confondus sont d'abord retirés (0 × ∞ au pied d'une descente). *)
let chemin ?z1 carte ws z0 =
  let ws =
    let l = ref [ ws.(0) ] in
    for i = 1 to Array.length ws - 1 do
      if ws.(i) <> ws.(i - 1) then l := ws.(i) :: !l
    done;
    Array.of_list (List.rev !l)
  in
  let n = Array.length ws in
  let z = Array.make n z0 in
  for i = 1 to n - 1 do
    let milieu = Complex.div (Complex.add ws.(i) ws.(i - 1)) { re = 2.; im = 0. } in
    z.(i) <- Complex.add z.(i - 1) (Complex.mul (derivee carte milieu) (Complex.sub ws.(i) ws.(i - 1)))
  done;
  (* np.cumsum depuis z0 : les sommes se font dans le même ordre *)
  match z1 with
  | None -> z
  | Some z1 ->
      let lg = Array.make n 0. in
      for i = 1 to n - 1 do
        lg.(i) <- lg.(i - 1) +. module_c (Complex.sub z.(i) z.(i - 1))
      done;
      let total = lg.(n - 1) in
      if total > 0. then
        let ecart = Complex.sub z1 z.(n - 1) in
        Array.mapi (fun i zi -> Complex.add zi (Complex.mul ecart { re = lg.(i) /. total; im = 0. })) z
      else z

(* Image d'un point intérieur : on y va en ligne droite depuis un point du bord loin des antécédents des sommets
   (partir d'une singularité rendrait l'intégration bruitée, et Newton oscillerait) ; points resserrés au départ. *)
let image carte (w : Complex.t) =
  let departs = Array.map (fun u -> w.re +. (w.im *. u)) (linspace (-0.5) 0.5 11) in
  let distance x = Array.fold_left (fun a wk -> Float.min a (Float.abs (wk -. x))) infinity carte.w in
  let x0 = ref departs.(0) in
  Array.iter (fun x -> if distance x > distance !x0 then x0 := x) departs;
  let x0 = !x0 in
  let ws =
    Array.map
      (fun u ->
        let f = 1. -. cos (Float.pi *. u /. 2.) in
        Complex.add { re = x0; im = 0. } (Complex.mul (Complex.sub w { re = x0; im = 0. }) { re = f; im = 0. }))
      (linspace 0. 1. 400)
  in
  let z = chemin carte ws (bord carte x0) in
  z.(Array.length z - 1)

(* Antécédent d'un point intérieur, par la méthode de Newton (les tables du bord sont interpolées : pas mieux que
   ~1e-6 près, on s'arrête à 1e-4). *)
let antecedent carte (z : Complex.t) =
  let rec newton w iteration =
    if iteration = 50 then raise (Pas_de_convergence "antécédent d'un point intérieur : Newton ne converge pas");
    let e = Complex.sub (image carte w) z in
    if module_c e < 1e-4 then w
    else
      let w = Complex.sub w (Complex.div e (derivee carte w)) in
      newton { w with im = Float.max w.im 1e-3 } (iteration + 1)
  in
  newton { re = z.re -. carte.delta; im = Float.max z.im 1. } 0

(* Demi-cercle du demi-plan de w0 à w1 (réels), n points resserrés aux extrémités. *)
let demi_cercle ?(n = 150) w0 w1 =
  let m = (w0 +. w1) /. 2. and rho = Float.abs (w1 -. w0) /. 2. in
  let phi0 = if w0 < w1 then Float.pi else 0. in
  Array.map
    (fun u ->
      let phi = phi0 +. ((Float.pi -. (2. *. phi0)) *. (1. -. cos (Float.pi *. u)) /. 2.) in
      { Complex.re = m +. (rho *. cos phi); im = rho *. sin phi })
    (linspace 0. 1. n)

(* --- 7b : une lettre du film (classe Lettre du Python) --- *)

open Geometrie

let sens_de_sigma = 1. (* comme dans NouvAutoMorph : σ_i positif = demi-tour horaire à l'écran *)

type lettre = {
  etats : Tresses.etat array;  (** l'image clé k (état 0) et l'image clé k+1 (état 1) *)
  sigma : Tresses.sigma Tresses.lettre;
  i : int;  (** indice de σ : les trous qui tournent sont i-1 et i (de 0) *)
  hauteur : float;
  largeur : float;
  geos : Tresses.geometrie array;  (** géométrie du dessin de chaque état *)
  h : float array array;  (** abscisses à l'écran des trous de chaque état *)
  n : int;  (** nombre de trous *)
  phys : int array array;  (** trou physique à chaque place, dans chaque état (i-1 et i échangés dans l'état 1) *)
  y_axe : float;
  clou : point;
  cache : (int * bool, float array) Hashtbl.t;
      (** écarts de la dernière carte calculée (état, haut ?), point de départ de Newton pour la suivante : seul état
          mutable, comme le [cache] du Python, dont dépendent les derniers chiffres des cartes *)
}

(* Une lettre σ entre l'image clé [cle] et l'image clé [suivante]. Les trous physiques sont numérotés comme dans
   l'état k ; dans l'état k+1, les places i-1 et i sont échangées. *)
let lettre ?(hauteur = 400.) ?(largeur = 400.) cle suivante sigma =
  let etats = [| cle; suivante |] in
  let geos = Array.map (Tresses.geometrie_etat ~hauteur ~largeur) etats in
  let h = Array.map2 (fun (e : Tresses.etat) g -> Array.map g.Tresses.abscisse e.trous) etats geos in
  let n = Array.length cle.Tresses.trous and i = sigma.Tresses.indice in
  let phys1 = Array.init n Fun.id in
  phys1.(i - 1) <- i;
  phys1.(i) <- i - 1;
  { etats; sigma; i; hauteur; largeur; geos; h; n; phys = [| Array.init n Fun.id; phys1 |]; y_axe = geos.(0).y_axe;
    clou = { x = largeur /. 2.; y = hauteur -. 10. }; cache = Hashtbl.create 4 }

let c re im = { Complex.re; im }

(* Position (complexe, y vers le haut, avant aplatissement) du trou physique p au temps s ; -1 et n : points
   virtuels au bord. Les trous qui ne tournent pas glissent de leur place dans l'image clé k à celle dans l'image clé
   k+1 ; les deux trous qui tournent font un demi-tour autour de leur milieu (centre et rayon glissent aussi). *)
let trou l p s =
  let i = l.i and h = l.h in
  if p < 0 then c 10. 0.
  else if p >= l.n then c (l.largeur -. 10.) 0.
  else if p <> i - 1 && p <> i then
    (* l'indice de p dans phys.(1) : p lui-même, puisque seuls i-1 et i sont échangés *)
    c (((1. -. s) *. h.(0).(p)) +. (s *. h.(1).(p))) 0.
  else
    let centre = ((1. -. s) *. (h.(0).(i - 1) +. h.(0).(i)) /. 2.) +. (s *. (h.(1).(i - 1) +. h.(1).(i)) /. 2.) in
    let r = ((1. -. s) *. (h.(0).(i) -. h.(0).(i - 1)) /. 2.) +. (s *. (h.(1).(i) -. h.(1).(i - 1)) /. 2.) in
    let sens = sens_de_sigma *. match l.sigma.signe with Tresses.Plus -> 1. | Moins -> -1. in
    let theta = Float.pi *. s in
    let a = if p = i - 1 then Float.pi -. (sens *. theta) else -.(sens *. theta) in
    c (centre +. (r *. cos a)) (r *. sin a)

let phys_de l e j = if j < 0 || j >= l.n then j else l.phys.(e).(j)

(* Sommets de la ligne brisée de l'état e au temps s : ses trous i-2, i-1, i, i+1 (ou points virtuels). *)
let ligne l e s = Array.init 4 (fun k -> trou l (phys_de l e (l.i - 2 + k)) s)

type pied = { morceau : int; longueur : float; position : Complex.t }
(* Le pied d'un point de l'état sur la ligne brisée : le morceau du bord (0 demi-droite de gauche, 1 à 3 les
   segments, 4 demi-droite de droite), la longueur parcourue sur ce morceau, sa position. *)

(* Pied du point d'abscisse x de l'état e au temps s, sur la ligne brisée de sommets v. Un point d'un des trois
   intervalles du bloc (autour des trous qui tournent) est posé sur le segment correspondant, à la même fraction ; les
   autres restent sur l'axe, à la même place relative entre les trous qui les encadrent. *)
let pied l e x s v =
  let i = l.i and n = l.n in
  let trous = l.etats.(e).Tresses.trous in
  let px = l.geos.(e).abscisse x in
  let cle j = if j < 0 then 10. else if j >= n then l.largeur -. 10. else l.h.(e).(j) in
  let actuel j = (trou l (phys_de l e j) s).re in
  let q = Tresses.intervalle x trous in
  if i - 1 <= q && q <= i + 1 then
    let f = (px -. cle (q - 1)) /. (cle q -. cle (q - 1)) in
    let p = q - i + 2 in
    let segment = Complex.sub v.(p) v.(p - 1) in
    { morceau = p; longueur = f *. module_c segment; position = Complex.add v.(p - 1) (Complex.mul (c f 0.) segment) }
  else
    let xa =
      if q = 0 then actuel 0 -. (cle 0 -. px)
      else if q = n then actuel (n - 1) +. (px -. cle (n - 1))
      else
        let f = (px -. cle (q - 1)) /. (cle q -. cle (q - 1)) in
        actuel (q - 1) +. (f *. (actuel q -. actuel (q - 1)))
    in
    if q < i - 1 then { morceau = 0; longueur = v.(0).re -. xa; position = c xa 0. }
    else { morceau = 4; longueur = xa -. v.(3).re; position = c xa 0. }

(* Les cartes du haut et du bas de l'état e au temps s (celle du bas : la ligne brisée symétrique), Newton parti des
   écarts de la carte précédente du même état. *)
let cartes l e s =
  let v = ligne l e s in
  let carte en_haut sommets =
    let carte = cree ?ecarts:(Hashtbl.find_opt l.cache (e, en_haut)) sommets in
    Hashtbl.replace l.cache (e, en_haut) carte.ecarts;
    carte
  in
  let haut = carte true v in
  let bas = carte false (Array.map Complex.conj v) in
  (v, haut, bas)

(* Aplatissement vertical au temps s : celui des images clés, mélangé, multiplié par la réduction (fixée image par
   image par le film quand le demi-tour fait sortir les arcs du cadre ; un champ modifié en place dans le Python). *)
let aplati l ~reduction s = (((1. -. s) *. l.geos.(0).aplati) +. (s *. l.geos.(1).aplati)) *. reduction

exception Clou_dans_un_demi_cercle

(* Lacets (polylignes à l'écran) de l'état e dessiné sur sa ligne brisée au temps s : chaque arc est l'image d'un
   demi-cercle du demi-plan entre les antécédents de ses pieds (arcs du haut par la carte du haut, du bas par celle du
   bas) ; les deux bouts descendent au clou par des géodésiques du demi-plan du bas. *)
let dessin l ~reduction e s =
  let v, haut, bas = cartes l e s in
  let aplati = aplati l ~reduction s and y_axe = l.y_axe in
  let ecran en_haut (zs : Complex.t array) =
    Array.map (fun (z : Complex.t) -> { x = z.re; y = (if en_haut then y_axe -. (z.im *. aplati) else y_axe +. (z.im *. aplati)) }) zs
  in
  let lacets = l.etats.(e).Tresses.lacets in
  let pieds = List.map (fun lacet -> Array.map (fun x -> pied l e x s v) lacet) lacets in
  let antecedents carte = List.map (Array.map (fun p -> antecedent_bord carte p.morceau p.longueur)) pieds in
  let wh = antecedents haut and wb = antecedents bas in
  let zc = c l.clou.x ((l.clou.y -. y_axe) /. aplati) in
  let wc = antecedent bas zc in
  (* le clou doit être hors des demi-cercles du bas (sinon les descentes croiseraient les arcs du bas) *)
  List.iter
    (fun w ->
      let j = ref 1 in
      while !j < Array.length w - 1 do
        let milieu = (w.(!j) +. w.(!j + 1)) /. 2. in
        if not (module_c (Complex.sub wc (c milieu 0.)) > Float.abs (w.(!j + 1) -. w.(!j)) /. 2.) then raise Clou_dans_un_demi_cercle;
        j := !j + 2
      done)
    wb;
  (* du pied (antécédent w, image z dans la carte du bas) au clou : la géodésique du demi-plan, arc du cercle
     orthogonal à l'axe qui passe par w et par l'antécédent du clou ; deux d'entre elles ne se recoupent qu'au clou *)
  let descente w z =
    let a = wc.re and b = wc.im in
    let u = Array.map (fun t -> 1. -. cos (Float.pi *. t /. 2.)) (linspace 0. 1. 200) in
    let ws =
      if Float.abs (a -. w) < 1e-9 *. (1. +. Float.abs b) then Array.map (fun f -> c (w +. (0. *. f)) (b *. f)) u
      else
        let m = ((a *. a) +. (b *. b) -. (w *. w)) /. (2. *. (a -. w)) in
        let rho = Float.abs (w -. m) in
        let phi0 = if w > m then 0. else Float.pi and phi1 = Float.atan2 b (a -. m) in
        Array.map (fun f -> let phi = phi0 +. ((phi1 -. phi0) *. f) in c (m +. (rho *. cos phi)) (rho *. sin phi)) u
    in
    ecran false (chemin ~z1:zc bas ws z)
  in
  List.map2
    (fun pl (h_, b_) ->
      let k = Array.length pl in
      let premier = renverse (descente b_.(0) (Complex.conj pl.(0).position)) in
      let arcs =
        List.init (k - 1) (fun j ->
            if j mod 2 = 0 then ecran true (chemin ~z1:pl.(j + 1).position haut (demi_cercle h_.(j) h_.(j + 1)) pl.(j).position)
            else
              ecran false
                (chemin ~z1:(Complex.conj pl.(j + 1).position) bas (demi_cercle b_.(j) b_.(j + 1)) (Complex.conj pl.(j).position)))
      in
      let dernier = descente b_.(k - 1) (Complex.conj pl.(k - 1).position) in
      Array.concat ((premier :: arcs) @ [ dernier ]))
    pieds (List.combine wh wb)

(* Ce que la carte projette, pour l'étude : les antécédents réels des sommets de la ligne brisée, celui du clou (dans le demi-plan du
   bas), et les arcs de chaque lacet comme demi-cercles du demi-plan w, entre les antécédents de leurs pieds (arcs du haut, puis du bas,
   en alternance), avec la ligne brisée elle-même (position complexe de ses sommets, y vers le haut, avant aplatissement). Travaille
   sur une copie du cache des cartes : n'influence pas le film. *)
type plan = {
  sommets : float array;  (** antécédents réels de L, A, B, R (dans l'ordre de la ligne brisée de l'état) *)
  w_clou : Complex.t;  (** antécédent du clou dans le demi-plan du bas *)
  arcs : (int * bool * float * float) list;  (** (lacet, arc du haut ?, w0, w1) *)
  ligne : Complex.t array;  (** les sommets de la ligne brisée *)
}

let plan_w l ~reduction e s =
  let l = { l with cache = Hashtbl.copy l.cache } in
  let v, haut, bas = cartes l e s in
  let pieds = List.map (fun lacet -> Array.map (fun x -> pied l e x s v) lacet) l.etats.(e).Tresses.lacets in
  let antecedents carte = List.map (Array.map (fun p -> antecedent_bord carte p.morceau p.longueur)) pieds in
  let wh = antecedents haut and wb = antecedents bas in
  let zc = c l.clou.x ((l.clou.y -. l.y_axe) /. aplati l ~reduction s) in
  let wc = antecedent bas zc in
  let arcs =
    List.concat
      (List.mapi
         (fun lacet (h_, b_) ->
           List.init (Array.length h_ - 1) (fun j -> if j mod 2 = 0 then (lacet, true, h_.(j), h_.(j + 1)) else (lacet, false, b_.(j), b_.(j + 1))))
         (List.combine wh wb))
  in
  { sommets = haut.w; w_clou = wc; arcs; ligne = v }

(* Point à l'écran d'un point z (y vers le haut, avant aplatissement) au temps s. *)
let ecran_de l ~reduction (z : Complex.t) s = { x = z.re; y = l.y_axe -. (z.im *. aplati l ~reduction s) }

(* Positions à l'écran des trous au temps s. *)
let trous_ecran l ~reduction s = Array.init l.n (fun p -> ecran_de l ~reduction (trou l p s) s)

(* Les lignes de construction à l'écran au temps s (Lettre.aretes du Python) : les morceaux de l'axe hors du bloc (de
   gauche à droite, du bord gauche au premier trou du bloc et du dernier au bord droit : les extrémités à ±10 000 sortent
   du cadre), puis, dans l'ordre, L–A, A–B, B–R, L–B et A–R (L, A, B, R : les trous i-2, i-1, i, i+1, les deux
   extrêmes pouvant être des points virtuels au bord de l'image). *)
let aretes l ~reduction s =
  let i = l.i and n = l.n in
  let t p = ecran_de l ~reduction (trou l p s) s in
  let lg = t (i - 2) and a = t (i - 1) and b = t i and r = t (i + 1) in
  let gauche =
    ({ x = -1e4; y = l.y_axe } :: List.init (max 0 (i - 1)) t) @ if i - 2 < 0 then [ lg ] else []
  and droite =
    List.init (max 0 (n - i - 1)) (fun k -> t (i + 1 + k)) @ (if i + 1 >= n then [ r ] else []) @ [ { x = 1e4; y = l.y_axe } ]
  in
  let paires = function [] -> [] | tete :: queue -> List.combine (List.filteri (fun k _ -> k < List.length queue) (tete :: queue)) queue in
  (paires gauche @ paires droite, [| (lg, a); (a, b); (b, r); (lg, b); (a, r) |])

(* --- L'essai « projection conforme seule » (mode conforme_pur du banc d'essai) -----------------------------------------
   Pas de carte, pas de triangulation : seuls les pieds sont posés sur les lignes de construction (la ligne brisée de l'état e
   au temps s, par [pied]) ; deux pieds consécutifs d'un lacet sont reliés par un arc de cercle de « bonne courbure » (la flèche
   de la demi-ellipse aplatie des images clés : aplati × demi-corde), du côté du haut ou du bas selon la parité de l'arc, sans
   souci des tangentes ; les deux bouts descendent au clou en ligne droite. Les croisements sont permis : l'essai sert à voir les
   erreurs de la projection seule. *)
(* Arc de cercle de p à q, du côté gauche de la marche si [c] > 0 (à droite si [c] < 0), de flèche |c| × aplati × demi-corde ; plat si c = 0. *)
let arc_signe ~c ~aplati p q =
  let d = q -: p in
  let corde = norme d in
  if corde < 1e-9 || Float.abs c < 1e-6 then [| p; q |]
  else begin
    let a = corde /. 2. and h = Float.abs c *. aplati *. corde /. 2. in
    let e = (1. /. corde) *: d in
    let n = { x = e.y; y = -.e.x } in
    let u = if c > 0. then n else oppose n in
    let rayon = ((a *. a) +. (h *. h)) /. (2. *. h) in
    let milieu = 0.5 *: (p +: q) in
    let centre = milieu -: ((rayon -. h) *: u) in
    let alpha = Float.asin (Float.min 1. (a /. rayon)) in
    Array.init 61 (fun j ->
        let phi = -.alpha +. (2. *. alpha *. float_of_int j /. 60.) in
        centre +: (rayon *: ((sin phi *: e) +: (cos phi *: u))))
  end

(* Le côté gauche de la marche de p à q (+1) ou droit (−1) qui regarde du côté de [hint] ; +1 si la corde est nulle. *)
let cote_vers p q hint =
  let d = q -: p in
  let corde = norme d in
  if corde < 1e-9 then 1. else if scalaire { x = d.y /. corde; y = -.d.x /. corde } hint >= 0. then 1. else -1.

let arc_vers ~hint ~aplati p q = arc_signe ~c:(cote_vers p q hint) ~aplati p q

(* Les pieds à l'écran de chaque lacet de l'état e au temps s, avec la normale à gauche de la ligne brisée (orientée de L à R) à chaque
   pied : un arc « du haut » regarde de ce côté-là, un arc « du bas » du côté opposé. Le haut de l'écran n'est que le cas de l'axe. *)
let pieds_normales l ~reduction e s =
  let v = ligne l e s in
  let ecr z = ecran_de l ~reduction z s in
  List.map
    (fun lacet ->
      Array.map
        (fun x ->
          let pd = pied l e x s v in
          let tangente =
            if pd.morceau >= 1 && pd.morceau <= 3 then
              let d = ecr v.(pd.morceau) -: ecr v.(pd.morceau - 1) in
              let n = norme d in
              if n < 1e-9 then { x = 1.; y = 0. } else (1. /. n) *: d
            else { x = 1.; y = 0. }
          in
          (ecr pd.position, { x = tangente.y; y = -.tangente.x }))
        lacet)
    l.etats.(e).Tresses.lacets

(* Les lacets de l'état e au temps s, et les pieds (à l'écran) de tous les lacets. *)
let dessin_pur l ~reduction e s =
  let aplati = aplati l ~reduction s in
  let pieds = pieds_normales l ~reduction e s in
  let lignes =
    List.map
      (fun pl ->
        let k = Array.length pl in
        let arcs =
          List.init (max 0 (k - 1)) (fun j ->
              let hint = (if j mod 2 = 0 then 1. else -1.) *: (snd pl.(j) +: snd pl.(j + 1)) in
              arc_vers ~hint ~aplati (fst pl.(j)) (fst pl.(j + 1)))
        in
        Array.concat (([| l.clou; fst pl.(0) |] :: arcs) @ [ [| fst pl.(k - 1); l.clou |] ]))
      pieds
  in
  (lignes, List.concat_map (fun pl -> List.map fst (Array.to_list pl)) pieds)

(* Un point de l'état non réduit après σ, au temps s : son départ (le pied du point ancien, ou celui de son père s'il est né), son
   arrivée (son pied dans l'état k+1, ou le milieu des départs des deux points qui s'annulent), son rôle (0 il glisse avec son trou,
   1 il tourne avec le bloc, 2 il est né sur un arc, 3 il s'annule : bigone) et l'indice, dans l'état k, de l'arc qui le suit dans le
   lacet (celui qu'il découpe, s'il est né). *)
type entree = { depart : point; arrivee : point; role : int; arc : int; nd : point; na : point }

let entrees l ~reduction s =
  let d = pieds_normales l ~reduction 0 s and a = pieds_normales l ~reduction 1 s in
  let non_reduit, origines = Tresses.agit_origines l.etats.(0) l.sigma in
  let bigs = Tresses.bigones non_reduit in
  List.mapi
    (fun lacet ((origines : Tresses.origine array), (rang, partenaire)) ->
      let dl = List.nth d lacet and al = List.nth a lacet in
      let borne t k = t.(max 0 (min (Array.length t - 1) k)) in
      let depart k = match origines.(k) with Tresses.Glisse j | Tresses.Tourne j | Tresses.Ne (j, _) -> borne dl j in
      Array.init (Array.length origines) (fun k ->
          let p, nd = depart k in
          let arc = match origines.(k) with Tresses.Glisse j | Tresses.Tourne j | Tresses.Ne (_, j) -> j in
          if rang.(k) >= 0 then
            let q, na = borne al rang.(k) in
            { depart = p; arrivee = q; arc; nd; na;
              role = (match origines.(k) with Tresses.Glisse _ -> 0 | Tresses.Tourne _ -> 1 | Tresses.Ne _ -> 2) }
          else { depart = p; arrivee = 0.5 *: (p +: fst (depart partenaire.(k))); arc; role = 3; nd; na = nd }))
    (List.combine origines bigs)

(* Les trajets des points de la lettre au temps s : (départ, arrivée, rôle). *)
let trajets l ~reduction s =
  List.concat_map (fun es -> List.map (fun e -> (e.depart, e.arrivee, e.role)) (Array.to_list es)) (entrees l ~reduction s)

(* Un chemin rééchantillonné en n points à égale distance le long de sa longueur. *)
let reechantillonne_cumul pl n =
  let m = Array.length pl in
  let cum = Array.make m 0. in
  for i = 1 to m - 1 do cum.(i) <- cum.(i - 1) +. norme (pl.(i) -: pl.(i - 1)) done;
  let total = cum.(m - 1) in
  if total < 1e-9 then Array.make n pl.(0)
  else begin
    let j = ref 0 in
    Array.init n (fun r ->
        let t = total *. float_of_int r /. float_of_int (n - 1) in
        while !j < m - 2 && cum.(!j + 1) < t do incr j done;
        let seg = cum.(!j + 1) -. cum.(!j) in
        let f = if seg < 1e-12 then 0. else (t -. cum.(!j)) /. seg in
        pl.(!j) +: (f *: (pl.(!j + 1) -: pl.(!j))))
  end

(* Les lacets en train de se transformer : à l'avancement w (0 : l'état k, 1 : l'état k+1), chaque point est entre son départ et son
   arrivée, et deux points consécutifs sont reliés par un arc de cercle dont le côté (à gauche ou à droite de la marche) passe de
   celui de l'état k (la parité de l'arc ancien) à celui de l'état k+1 (la parité dans le lacet non réduit). Entre deux points qui
   survivent, les points qui s'annulent se rejoignent ; sur la seconde moitié du mouvement, le chemin qui passe par eux est fondu
   (à égale longueur) dans l'arc direct entre les deux survivants, qui est ce qu'il en reste à l'arrivée. *)
let dessin_morph l ~reduction s w =
  let aplati = aplati l ~reduction s in
  let haut x = if x mod 2 = 0 then 1. else -1. in
  let beta = let u = Float.min 1. (Float.max 0. ((w -. 0.5) /. 0.5)) in u *. u *. (3. -. (2. *. u)) in
  List.map
    (fun es ->
      let k = Array.length es in
      let pos = Array.map (fun e -> ((1. -. w) *: e.depart) +: (w *: e.arrivee)) es in
      let pt i = if i < 0 || i >= k then l.clou else pos.(i) in
      let piece i =
        if i < 0 || i >= k - 1 then [| pt i; pt (i + 1) |]
        else begin
          let c1 = cote_vers es.(i).arrivee es.(i + 1).arrivee (haut i *: (es.(i).na +: es.(i + 1).na)) in
          let c0 =
            if norme (es.(i + 1).depart -: es.(i).depart) < 1e-6 then c1
            else cote_vers es.(i).depart es.(i + 1).depart (haut es.(i).arc *: (es.(i).nd +: es.(i + 1).nd))
          in
          arc_signe ~c:(((1. -. w) *. c0) +. (w *. c1)) ~aplati pos.(i) pos.(i + 1)
        end
      in
      let survivants =
        (-1) :: (List.filter (fun i -> es.(i).role <> 3) (List.init k Fun.id)) @ [ k ]
      in
      let rec chemins = function
        | a :: (b :: _ as reste) ->
            let c =
              if b = a + 1 then piece a
              else begin
                let u = Array.concat (List.init (b - a) (fun d -> piece (a + d))) in
                if beta <= 0. then u
                else begin
                  let r =
                    if a < 0 || b >= k then [| pt a; pt b |]
                    else arc_vers ~hint:(haut a *: (es.(a).na +: es.(b).na)) ~aplati (pt a) (pt b)
                  in
                  let u = reechantillonne_cumul u 120 and r = reechantillonne_cumul r 120 in
                  Array.init 120 (fun j -> ((1. -. beta) *: u.(j)) +: (beta *: r.(j)))
                end
              end
            in
            c :: chemins reste
        | _ -> []
      in
      Array.concat (chemins survivants))
    (entrees l ~reduction s)
