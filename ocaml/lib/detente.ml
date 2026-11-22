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

(* Distance du point (cx, cy) au segment [(ax, ay), (bx, by)]. *)
let distance_segment ax ay bx by cx cy =
  let abx = bx -. ax and aby = by -. ay in
  let l2 = Float.max ((abx *. abx) +. (aby *. aby)) 1e-12 in
  let u = Float.min 1. (Float.max 0. ((((cx -. ax) *. abx) +. ((cy -. ay) *. aby)) /. l2)) in
  Float.sqrt (((ax +. (u *. abx) -. cx) ** 2.) +. ((ay +. (u *. aby) -. cy) ** 2.))

(* Garde des points à peu près réguliers sans jamais rapprocher la courbe d'un trou (le rééchantillonnage, qui remplace la courbe
   par des cordes, coupe à l'intérieur des boucles serrées ; répété, il amenait un brin sur son trou) : les segments plus longs que
   1,5 pas sont découpés par des points pris sur eux (la courbe ne bouge pas) ; un point dont un segment est plus court qu'un
   demi-pas est retiré (fusion) seulement si la corde qui le remplace ne dépasse pas 1,2 pas et n'est pas plus près d'un trou que les
   deux segments retirés. Une corde peut couper un brin voisin : le film vérifie après coup et refait la retouche sans fusion. *)
let retouche ?(fusion = true) pas (trous : point array) xs ys =
  let m = Array.length xs in
  let px = ref [ xs.(0) ] and py = ref [ ys.(0) ] in
  for i = 1 to m - 1 do
    let ax = List.hd !px and ay = List.hd !py in
    let l = Float.sqrt (((xs.(i) -. ax) ** 2.) +. ((ys.(i) -. ay) ** 2.)) in
    let k = if l > 1.5 *. pas then int_of_float (Float.ceil (l /. pas)) else 1 in
    for j = 1 to k - 1 do
      let f = float_of_int j /. float_of_int k in
      px := (ax +. ((xs.(i) -. ax) *. f)) :: !px;
      py := (ay +. ((ys.(i) -. ay) *. f)) :: !py
    done;
    px := xs.(i) :: !px;
    py := ys.(i) :: !py
  done;
  let ax_ = Array.of_list (List.rev !px) and ay_ = Array.of_list (List.rev !py) in
  let n = Array.length ax_ in
  let gx = ref [ ax_.(0) ] and gy = ref [ ay_.(0) ] in
  for i = 1 to n - 2 do
    let a_x = List.hd !gx and a_y = List.hd !gy and m_x = ax_.(i) and m_y = ay_.(i) and b_x = ax_.(i + 1) and b_y = ay_.(i + 1) in
    let court = Float.min (Float.sqrt (((m_x -. a_x) ** 2.) +. ((m_y -. a_y) ** 2.))) (Float.sqrt (((b_x -. m_x) ** 2.) +. ((b_y -. m_y) ** 2.))) < 0.5 *. pas in
    let sans_danger () =
      Array.for_all
        (fun (t : point) ->
          distance_segment a_x a_y b_x b_y t.x t.y
          >= Float.min (distance_segment a_x a_y m_x m_y t.x t.y) (distance_segment m_x m_y b_x b_y t.x t.y))
        trous
    in
    (* la corde ne doit pas être trop longue elle-même, sinon elle serait redécoupée à l'itération suivante *)
    let corde_courte = Float.sqrt (((b_x -. a_x) ** 2.) +. ((b_y -. a_y) ** 2.)) <= 1.2 *. pas in
    if not (fusion && court && corde_courte && sans_danger ()) then begin
      gx := m_x :: !gx;
      gy := m_y :: !gy
    end
  done;
  gx := ax_.(n - 1) :: !gx;
  gy := ay_.(n - 1) :: !gy;
  (Array.of_list (List.rev !gx), Array.of_list (List.rev !gy))

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
   [ecart_indices]) : une grille de pas [rayon], les points rangés par case (listes chaînées, sans tri : le tri est lent une fois
   compilé en JS), chaque point comparé aux 9 cases autour. *)
let paires_proches xs ys lacet indice rayon ecart_indices =
  let n = Array.length xs in
  if n = 0 then ([||], [||])
  else begin
    (* une grille de pas [rayon] sur la boîte des points ; chaque case tient la liste de ses points (tête, suivant) *)
    let minx = Array.fold_left Float.min infinity xs and miny = Array.fold_left Float.min infinity ys in
    let cx = Array.map (fun x -> int_of_float ((x -. minx) /. rayon)) xs and cy = Array.map (fun y -> int_of_float ((y -. miny) /. rayon)) ys in
    let gw = Array.fold_left max 0 cx + 1 and gh = Array.fold_left max 0 cy + 1 in
    let tete = Array.make (gw * gh) (-1) and suivant = Array.make n (-1) in
    for i = n - 1 downto 0 do
      let c = (cy.(i) * gw) + cx.(i) in
      suivant.(i) <- tete.(c);
      tete.(c) <- i
    done;
    let pi = pile () and pj = pile () in
    let r2 = rayon *. rayon in
    for i = 0 to n - 1 do
      for dy = -1 to 1 do
        let y = cy.(i) + dy in
        if y >= 0 && y < gh then
          for dx = -1 to 1 do
            let x = cx.(i) + dx in
            if x >= 0 && x < gw then begin
              let j = ref tete.((y * gw) + x) in
              while !j >= 0 do
                let jj = !j in
                if jj > i then begin
                  let ex = xs.(i) -. xs.(jj) and ey = ys.(i) -. ys.(jj) in
                  if (ex *. ex) +. (ey *. ey) < r2 && not (lacet.(i) = lacet.(jj) && abs (indice.(i) - indice.(jj)) < ecart_indices) then begin
                    empile pi i;
                    empile pj jj
                  end
                end;
                j := suivant.(jj)
              done
            end
          done
      done
    done;
    (Array.sub pi.donnees 0 pi.taille, Array.sub pj.donnees 0 pj.taille)
  end

let clip a b v = Float.min b (Float.max a v)

(* Deux segments de brins (s : points s, s + 1) se croisent-ils ? Parmi les segments voisins des paires proches (pi, pj), hors des
   12 px autour du clou (les brins s'y rejoignent) ; [existe s] : le segment s est dans un brin. *)
let croisement_existe xs ys existe pi pj (clou : point) pas =
  let n = Array.length xs in
  let loin i = Float.sqrt (((xs.(i) -. clou.x) ** 2.) +. ((ys.(i) -. clou.y) ** 2.)) > 12. in
  let teste sa sb =
    sa >= 0 && sb >= 0 && sa < n - 1 && sb < n - 1 && existe.(sa) && existe.(sb) && abs (sa - sb) > 1
    && loin sa && loin (sa + 1) && loin sb && loin (sb + 1)
    &&
    let d1x = xs.(sa + 1) -. xs.(sa) and d1y = ys.(sa + 1) -. ys.(sa) and d2x = xs.(sb + 1) -. xs.(sb) and d2y = ys.(sb + 1) -. ys.(sb) in
    let den = (d1x *. d2y) -. (d1y *. d2x) in
    den <> 0.
    &&
    let wx = xs.(sb) -. xs.(sa) and wy = ys.(sb) -. ys.(sa) in
    let t = ((wx *. d2y) -. (wy *. d2x)) /. den and u = ((wx *. d1y) -. (wy *. d1x)) /. den in
    t >= 0. && t <= 1. && u >= 0. && u <= 1.
  in
  let trouve = ref false and q = ref 0 in
  while (not !trouve) && !q < Array.length pi do
    let i = pi.(!q) and j = pj.(!q) in
    if Float.sqrt (((xs.(i) -. xs.(j)) ** 2.) +. ((ys.(i) -. ys.(j)) ** 2.)) < 4. *. pas then
      List.iter (fun (sa, sb) -> if teste sa sb then trouve := true) [ (i - 1, j - 1); (i, j - 1); (i - 1, j); (i, j) ];
    incr q
  done;
  !trouve

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
    (* avant de rééchantillonner, éloigner des trous les points trop proches : une boucle plus petite que le pas, rééchantillonnée,
       peut ne plus contenir son trou (le brin l'aurait sauté avant même la première itération). Dilatation radiale autour de
       chaque trou, la distance d devenant d + force b (1 − d / 2b) en deçà de 2b (b : la barrière) : elle garde l'ordre des
       distances, aucun brin n'en croise un autre ni ne passe par-dessus le trou ; nulle à force 0 (le film reste continu). *)
    let barriere = Float.max (0.6 *. r.rayon_trou) (0.75 *. r.pas) in
    let dilate (p : point) =
      Array.fold_left
        (fun (p : point) (t : point) ->
          let dx = p.x -. t.x and dy = p.y -. t.y in
          let d = longueur dx dy in
          if d < 2. *. barriere && d > 1e-9 then begin
            let nouveau = d +. (force *. barriere *. (1. -. (d /. (2. *. barriere)))) in
            { x = t.x +. (dx *. nouveau /. d); y = t.y +. (dy *. nouveau /. d) }
          end
          else p)
        p trous
    in
    (* les bouts restent en place : ceux des arcs (diagramme de courbes) sont sur un trou ou un point fixe *)
    let lignes = List.map (fun l -> Array.mapi (fun i p -> if i = 0 || i = Array.length l - 1 then p else dilate p) l) lignes in
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
      let avx = Array.copy xs_ and avy = Array.copy ys_ in
      for i = 0 to n - 1 do
        xs_.(i) <- xs_.(i) +. fx.(i);
        ys_.(i) <- ys_.(i) +. fy.(i)
      done;
      (* la barrière des trous : un segment qui passerait plus près d'un trou que [barriere], en s'en rapprochant, reprend sa position
         d'avant (ses deux bouts). Revenir à une position juste ne peut ni croiser un brin voisin ni sauter le trou (pousser le segment
         le pouvait), et la distance d'un segment à un trou, une fois sous la barrière, ne diminue plus. On recommence tant qu'un
         retour en arrière en a fait passer un autre sous la barrière. *)
      let barriere = Float.max (0.6 *. r.rayon_trou) (0.75 *. r.pas) in
      let distance px py i (t : point) =
        let ax = px.(i) and ay = py.(i) and abx = px.(i + 1) -. px.(i) and aby = py.(i + 1) -. py.(i) in
        let l2 = Float.max ((abx *. abx) +. (aby *. aby)) 1e-12 in
        let u = clip 0. 1. ((((t.x -. ax) *. abx) +. ((t.y -. ay) *. aby)) /. l2) in
        longueur (ax +. (u *. abx) -. t.x) (ay +. (u *. aby) -. t.y)
      in
      let encore = ref true and passes = ref 0 in
      while !encore && !passes < 20 do
        incr passes;
        let retour = Array.make n false in
        Array.iter
          (fun t ->
            for k = 0 to nb_brins - 1 do
              for i = b.(k) to b.(k + 1) - 2 do
                (* un segment (de longueur sous 2 pas) dont un bout est à plus de barriere + 2 pas du trou ne peut pas l'approcher *)
                if longueur (xs_.(i) -. t.x) (ys_.(i) -. t.y) < barriere +. (2. *. r.pas) then
                let dn = distance xs_ ys_ i t in
                if dn < barriere && dn < distance avx avy i t -. 1e-12 then begin
                  retour.(i) <- true;
                  retour.(i + 1) <- true
                end
              done
            done)
          trous;
        encore := false;
        for i = 0 to n - 1 do
          if retour.(i) && (xs_.(i) <> avx.(i) || ys_.(i) <> avy.(i)) then begin
            xs_.(i) <- avx.(i);
            ys_.(i) <- avy.(i);
            encore := true
          end
        done
      done;
      (* pas de croisement entre brins : si un segment en croise un autre (d'un autre brin, ou un passage éloigné du même), les points
         des deux reprennent leur position d'avant ; le dessin de départ n'en a pas, il n'en aura donc jamais. Les segments qui se
         croisent ont des bouts à moins d'un pas et demi : ils sont dans les paires proches. *)
      let existe = Array.make n false in
      for k = 0 to nb_brins - 1 do
        for i = b.(k) to b.(k + 1) - 2 do existe.(i) <- true done
      done;
      let loin_clou = Array.init n (fun i -> longueur (xs_.(i) -. clou.x) (ys_.(i) -. clou.y) > 12.) in
      let loin i = loin_clou.(i) in
      let teste sa sb =
        sa >= 0 && sb >= 0 && sa < n - 1 && sb < n - 1 && existe.(sa) && existe.(sb) && abs (sa - sb) > 1
        && loin sa && loin (sa + 1) && loin sb && loin (sb + 1)
        &&
        let d1x = xs_.(sa + 1) -. xs_.(sa) and d1y = ys_.(sa + 1) -. ys_.(sa) in
        let d2x = xs_.(sb + 1) -. xs_.(sb) and d2y = ys_.(sb + 1) -. ys_.(sb) in
        let den = (d1x *. d2y) -. (d1y *. d2x) in
        den <> 0.
        &&
        let wx = xs_.(sb) -. xs_.(sa) and wy = ys_.(sb) -. ys_.(sa) in
        let t = ((wx *. d2y) -. (wy *. d2x)) /. den and u = ((wx *. d1y) -. (wy *. d1x)) /. den in
        t >= 0. && t <= 1. && u >= 0. && u <= 1.
      in
      let ai = !pi and aj = !pj in
      let encore = ref true and passes = ref 0 in
      while !encore && !passes < 20 do
        incr passes;
        let retour = Array.make n false in
        for q = 0 to Array.length ai - 1 do
          let i = ai.(q) and j = aj.(q) in
          (* deux segments de longueur sous 2 pas qui se croisent ont deux bouts à moins de 2 pas *)
          if longueur (xs_.(i) -. xs_.(j)) (ys_.(i) -. ys_.(j)) < 4. *. r.pas then
          List.iter
            (fun (sa, sb) ->
              if teste sa sb then begin
                retour.(sa) <- true; retour.(sa + 1) <- true; retour.(sb) <- true; retour.(sb + 1) <- true
              end)
            [ (i - 1, j - 1); (i, j - 1); (i - 1, j); (i, j) ]
        done;
        encore := false;
        for i = 0 to n - 1 do
          if retour.(i) && (xs_.(i) <> avx.(i) || ys_.(i) <> avy.(i)) then begin
            xs_.(i) <- avx.(i);
            ys_.(i) <- avy.(i);
            encore := true
          end
        done
      done;
      (* rééchantillonner pour garder des points réguliers *)
      (* toutes les 25 itérations, et dès qu'un segment dépasse 2 pas (les croisements sont bloqués plus loin, mais leur détection
         suppose des segments assez courts pour que leurs bouts soient dans les paires proches) *)
      let trop_long = ref false in
      for k = 0 to nb_brins - 1 do
        for i = b.(k) to b.(k + 1) - 2 do
          if longueur (xs_.(i + 1) -. xs_.(i)) (ys_.(i + 1) -. ys_.(i)) > 2. *. r.pas then trop_long := true
        done
      done;
      if (it mod 25 = 24 || !trop_long) && it < r.iterations - 1 then begin
        let retouche_tout fusion =
          installe
            (List.init nb_brins (fun k ->
                 let a = b.(k) and m = b.(k + 1) - b.(k) in
                 retouche ~fusion r.pas trous (Array.sub xs_ a m) (Array.sub ys_ a m)));
          cherche ()
        in
        retouche_tout true;
        (* une fusion a pu faire couper un brin voisin par sa corde : on refait alors la retouche sans fusion *)
        let existe = Array.make (Array.length !xs) false in
        let b2 = !bornes in
        for k = 0 to nb_brins - 1 do
          for i = b2.(k) to b2.(k + 1) - 2 do existe.(i) <- true done
        done;
        if croisement_existe !xs !ys existe !pi !pj clou r.pas then retouche_tout false
      end
    done;
    let b = !bornes in
    List.init nb_brins (fun k -> Array.init (b.(k + 1) - b.(k)) (fun i -> { x = !xs.(b.(k) + i); y = !ys.(b.(k) + i) }))
  end
