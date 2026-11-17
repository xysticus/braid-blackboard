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
  let longueurs = Array.map Complex.norm cotes_c in
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
        lg.(i) <- lg.(i - 1) +. Complex.norm (Complex.sub z.(i) z.(i - 1))
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
    if Complex.norm e < 1e-4 then w
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
