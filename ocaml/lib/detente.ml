(* La détente du raccord (etude/lacets/essai_lissage.py) : un court flot de courbure contraint, appliqué au dessin du
   film conforme pendant la fenêtre du raccord.

   Chaque brin est rééchantillonné à pas régulier, puis on itère :
   - la tension (flot de courbure discret : chaque point va vers le milieu de ses deux voisins), qui arrondit les coins
     et efface les zigzags ;
   - la répulsion entre points de brins différents (et entre passages éloignés d'un même brin) plus proches que
     [ecart], éteinte près du clou, et entre un brin et un trou plus proche que [rayon_trou] ;
   avec un pas par itération borné ([pas_max]) : un brin ne peut sauter ni par-dessus un autre, ni par-dessus un trou.
   L'intensité [force] ∈ [0, 1] multiplie chaque pas ; près du clou, elle s'éteint aussi (le faisceau y garde sa forme).

   Mêmes calculs que le Python (à l'ordre des sommes près : les forces de répulsion y sont ajoutées par np.add.at dans
   un autre ordre) ; les voisins sont cherchés par une grille au lieu de paquets de distances (même ensemble de paires). *)

open Geometrie

type reglages = {
  pas : float;  (** du rééchantillonnage *)
  ecart : float;  (** écart minimal entre deux brins *)
  rayon_trou : float;  (** distance minimale d'un brin à un trou *)
  rayon_clou : float;  (** la répulsion s'éteint en deçà, vers le clou *)
  calme_clou : float;  (** la détente aussi, progressivement entre 10 et cette distance *)
  iterations : int;
  tension : float;
  repulsion : float;
  pas_max : float;
}

let defaut =
  { pas = 4.; ecart = 6.; rayon_trou = 12.; rayon_clou = 150.; calme_clou = 40.; iterations = 400; tension = 0.25; repulsion = 0.5; pas_max = 0.3 }

(* np.interp sur une table croissante (les longueurs cumulées). *)
let interp x xp fp =
  let n = Array.length xp in
  if x <= xp.(0) then fp.(0)
  else if x >= xp.(n - 1) then fp.(n - 1)
  else begin
    let bas = ref 0 and haut = ref (n - 1) in
    while !haut - !bas > 1 do
      let m = (!bas + !haut) / 2 in
      if xp.(m) <= x then bas := m else haut := m
    done;
    let j = !bas in
    ((fp.(j + 1) -. fp.(j)) /. (xp.(j + 1) -. xp.(j)) *. (x -. xp.(j))) +. fp.(j)
  end

(* La polyligne (xs, ys) à pas régulier, les deux bouts gardés (le reechantillonne du Python). *)
let reechantillonne pas xs ys =
  let m = Array.length xs in
  let l = Array.make m 0. in
  for k = 1 to m - 1 do
    l.(k) <- l.(k - 1) +. Float.sqrt (((xs.(k) -. xs.(k - 1)) ** 2.) +. ((ys.(k) -. ys.(k - 1)) ** 2.))
  done;
  let total = l.(m - 1) in
  let n = max 2 (int_of_float (Float.round (total /. pas)) + 1) in
  let t = Conforme.linspace 0. total n in
  (Array.map (fun ti -> interp ti l xs) t, Array.map (fun ti -> interp ti l ys) t)

(* Tableau d'entiers qui grandit. *)
type pile = { mutable donnees : int array; mutable taille : int }

let pile () = { donnees = Array.make 1024 0; taille = 0 }

let empile p v =
  if p.taille = Array.length p.donnees then begin
    let d = Array.make (2 * p.taille) 0 in
    Array.blit p.donnees 0 d 0 p.taille;
    p.donnees <- d
  end;
  p.donnees.(p.taille) <- v;
  p.taille <- p.taille + 1

(* Les paires (i, j), i < j, de points à moins de [rayon], sauf deux points voisins d'un même brin (indices à moins de
   [ecart_indices]) : une grille de pas [rayon], les points rangés par case, chaque point comparé aux 9 cases autour. *)
let paires_proches xs ys lacet indice rayon ecart_indices =
  let n = Array.length xs in
  let case v = int_of_float (Float.floor (v /. rayon)) in
  let cle cx cy = (cx * 1_000_003) + cy in
  let cles = Array.init n (fun i -> cle (case xs.(i)) (case ys.(i))) in
  let ordre = Array.init n Fun.id in
  Array.sort (fun a b -> compare cles.(a) cles.(b)) ordre;
  let triees = Array.map (fun i -> cles.(i)) ordre in
  (* le premier indice de [triees] dont la clé est >= k *)
  let premier k =
    let bas = ref 0 and haut = ref n in
    while !bas < !haut do
      let m = (!bas + !haut) / 2 in
      if triees.(m) < k then bas := m + 1 else haut := m
    done;
    !bas
  in
  let pi = pile () and pj = pile () in
  let r2 = rayon *. rayon in
  for i = 0 to n - 1 do
    let cx = case xs.(i) and cy = case ys.(i) in
    for dx = -1 to 1 do
      for dy = -1 to 1 do
        let k = cle (cx + dx) (cy + dy) in
        let a = ref (premier k) in
        while !a < n && triees.(!a) = k do
          let j = ordre.(!a) in
          if j > i then begin
            let ex = xs.(i) -. xs.(j) and ey = ys.(i) -. ys.(j) in
            if (ex *. ex) +. (ey *. ey) < r2 && not (lacet.(i) = lacet.(j) && abs (indice.(i) - indice.(j)) < ecart_indices) then begin
              empile pi i;
              empile pj j
            end
          end;
          incr a
        done
      done
    done
  done;
  (Array.sub pi.donnees 0 pi.taille, Array.sub pj.donnees 0 pj.taille)

let clip a b v = Float.min b (Float.max a v)

(* Longueur d'un vecteur : sqrt plutôt que Float.hypot, que js_of_ocaml traduit par Math.hypot, très lent. *)
let longueur dx dy = Float.sqrt ((dx *. dx) +. (dy *. dy))

(* Le dessin détendu ; [force] ∈ [0, 1] (0 : le dessin tel quel). *)
let detend ?(reglages = defaut) (lignes : point array list) (trous : point array) (clou : point) force =
  if force <= 0. then lignes
  else begin
    let r = reglages in
    (* l'état : les points de tous les brins à la suite, et pour chaque brin ses bornes *)
    let xs = ref [||] and ys = ref [||] and lacet = ref [||] and indice = ref [||] and bornes = ref [||] in
    let installe brins =
      let tailles = List.map (fun (bx, _) -> Array.length bx) brins in
      xs := Array.concat (List.map fst brins);
      ys := Array.concat (List.map snd brins);
      lacet := Array.concat (List.mapi (fun k n -> Array.make n k) tailles);
      indice := Array.concat (List.map (fun n -> Array.init n Fun.id) tailles);
      let b = Array.make (List.length tailles + 1) 0 in
      List.iteri (fun k n -> b.(k + 1) <- b.(k) + n) tailles;
      bornes := b
    in
    installe (List.map (fun l -> reechantillonne r.pas (Array.map (fun p -> p.x) l) (Array.map (fun p -> p.y) l)) lignes);
    let ecart_indices = int_of_float (Float.ceil (2.5 *. r.ecart /. r.pas)) + 2 in
    let pi = ref [||] and pj = ref [||] in
    let cherche () =
      (* les paires sont cherchées toutes les 8 itérations : dans l'intervalle, deux points se rapprochent d'au plus 16 pas_max ;
         on les cherche donc jusqu'à 1,6 ecart + 16 pas_max, sinon deux brins pourraient passer sous l'écart sans se repousser *)
      let a, b = paires_proches !xs !ys !lacet !indice ((1.6 *. r.ecart) +. (16. *. r.pas_max)) ecart_indices in
      pi := a;
      pj := b
    in
    let nb_brins = List.length lignes in
    for it = 0 to r.iterations - 1 do
      if it mod 8 = 0 then cherche ();
      let xs_ = !xs and ys_ = !ys and b = !bornes in
      let n = Array.length xs_ in
      let fx = Array.make n 0. and fy = Array.make n 0. in
      let au_clou = Array.init n (fun i -> longueur (xs_.(i) -. clou.x) (ys_.(i) -. clou.y)) in
      (* la tension ; les bouts de chaque brin (au clou) sont leurs propres voisins *)
      for k = 0 to nb_brins - 1 do
        for i = b.(k) to b.(k + 1) - 1 do
          let p = if i = b.(k) then i else i - 1 and s = if i = b.(k + 1) - 1 then i else i + 1 in
          fx.(i) <- r.tension *. (((xs_.(p) +. xs_.(s)) /. 2.) -. xs_.(i));
          fy.(i) <- r.tension *. (((ys_.(p) +. ys_.(s)) /. 2.) -. ys_.(i))
        done
      done;
      (* la répulsion entre brins, éteinte près du clou *)
      let ai = !pi and aj = !pj in
      for q = 0 to Array.length ai - 1 do
        let i = ai.(q) and j = aj.(q) in
        let dx = xs_.(i) -. xs_.(j) and dy = ys_.(i) -. ys_.(j) in
        let d = longueur dx dy in
        let proche = Float.min au_clou.(i) au_clou.(j) in
        let ecart = r.ecart *. clip 0. 1. (proche /. r.rayon_clou) in
        if d < ecart && d > 1e-9 then begin
          let c = r.repulsion *. (ecart -. d) /. d /. 2. in
          fx.(i) <- fx.(i) +. (c *. dx);
          fy.(i) <- fy.(i) +. (c *. dy);
          fx.(j) <- fx.(j) -. (c *. dx);
          fy.(j) <- fy.(j) -. (c *. dy)
        end
      done;
      (* la répulsion des trous *)
      Array.iter
        (fun t ->
          for i = 0 to n - 1 do
            let dx = xs_.(i) -. t.x and dy = ys_.(i) -. t.y in
            let d = longueur dx dy in
            if d < r.rayon_trou && d > 1e-9 then begin
              let c = r.repulsion *. (r.rayon_trou -. d) /. d in
              fx.(i) <- fx.(i) +. (c *. dx);
              fy.(i) <- fy.(i) +. (c *. dy)
            end
          done)
        trous;
      (* l'intensité, éteinte près du clou ; le pas borné ; les bouts fixes *)
      for i = 0 to n - 1 do
        let calme = clip 0. 1. ((au_clou.(i) -. 10.) /. (r.calme_clou -. 10.)) in
        let gx = fx.(i) *. force *. calme and gy = fy.(i) *. force *. calme in
        let g = longueur gx gy in
        let gx, gy = if g > r.pas_max then (gx *. r.pas_max /. g, gy *. r.pas_max /. g) else (gx, gy) in
        fx.(i) <- gx;
        fy.(i) <- gy
      done;
      for k = 0 to nb_brins - 1 do
        fx.(b.(k)) <- 0.; fy.(b.(k)) <- 0.;
        fx.(b.(k + 1) - 1) <- 0.; fy.(b.(k + 1) - 1) <- 0.
      done;
      for i = 0 to n - 1 do
        xs_.(i) <- xs_.(i) +. fx.(i);
        ys_.(i) <- ys_.(i) +. fy.(i)
      done;
      (* la barrière des trous, sur les segments et pas seulement les points : la répulsion n'est qu'une force, que la tension des
         boucles serrées peut vaincre, et deux points écartés peuvent laisser entre eux un segment qui enjambe le trou. Un segment
         plus proche d'un trou que [barriere] est repoussé en bloc (ses deux bouts du même vecteur, moyenné si un bout est poussé
         par ses deux segments), de [pas_max] au plus : un segment ne s'approche pas plus vite d'un trou, il ne peut donc plus passer
         par-dessus, et une poussée plus forte le ferait sauter par-dessus un brin voisin. *)
      let barriere = Float.max (0.6 *. r.rayon_trou) (0.75 *. r.pas) in
      Array.iter
        (fun t ->
          let px = Array.make n 0. and py = Array.make n 0. and compte = Array.make n 0 in
          let touche = ref false in
          for k = 0 to nb_brins - 1 do
            for i = b.(k) to b.(k + 1) - 2 do
              let ax = xs_.(i) and ay = ys_.(i) and abx = xs_.(i + 1) -. xs_.(i) and aby = ys_.(i + 1) -. ys_.(i) in
              let l2 = Float.max ((abx *. abx) +. (aby *. aby)) 1e-12 in
              let u = clip 0. 1. ((((t.x -. ax) *. abx) +. ((t.y -. ay) *. aby)) /. l2) in
              let vx = ax +. (u *. abx) -. t.x and vy = ay +. (u *. aby) -. t.y in
              let ds = longueur vx vy in
              if ds < barriere && ds > 1e-9 then begin
                let c = Float.min (barriere -. ds) r.pas_max /. ds in   (* pas plus que pas_max : sinon le segment saute par-dessus un brin voisin *)
                px.(i) <- px.(i) +. (c *. vx); py.(i) <- py.(i) +. (c *. vy); compte.(i) <- compte.(i) + 1;
                px.(i + 1) <- px.(i + 1) +. (c *. vx); py.(i + 1) <- py.(i + 1) +. (c *. vy); compte.(i + 1) <- compte.(i + 1) + 1;
                touche := true
              end
            done
          done;
          if !touche then begin
            let fixe i = Array.exists (fun k -> i = b.(k) || i = b.(k + 1) - 1) (Array.init nb_brins Fun.id) in
            for i = 0 to n - 1 do
              if compte.(i) > 0 && not (fixe i) then begin
                xs_.(i) <- xs_.(i) +. (px.(i) /. float_of_int compte.(i));
                ys_.(i) <- ys_.(i) +. (py.(i) /. float_of_int compte.(i))
              end
            done
          end)
        trous;
      (* rééchantillonner pour garder des points réguliers *)
      (* toutes les 25 itérations, et dès qu'un segment dépasse 1,5 pas : la répulsion n'agit qu'entre les points, deux longs
         segments pourraient se croiser, leurs points restant écartés *)
      let trop_long = ref false in
      for k = 0 to nb_brins - 1 do
        for i = b.(k) to b.(k + 1) - 2 do
          if longueur (xs_.(i + 1) -. xs_.(i)) (ys_.(i + 1) -. ys_.(i)) > 1.5 *. r.pas then trop_long := true
        done
      done;
      if (it mod 25 = 24 || !trop_long) && it < r.iterations - 1 then begin
        installe
          (List.init nb_brins (fun k ->
               let a = b.(k) and m = b.(k + 1) - b.(k) in
               reechantillonne r.pas (Array.sub xs_ a m) (Array.sub ys_ a m)));
        cherche ()
      end
    done;
    let b = !bornes in
    List.init nb_brins (fun k -> Array.init (b.(k + 1) - b.(k)) (fun i -> { x = !xs.(b.(k) + i); y = !ys.(b.(k) + i) }))
  end
