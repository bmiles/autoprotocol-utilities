from container_helpers import plates_needed, first_empty_well, unique_containers
from misc_helpers import printdate
from autoprotocol.container import Container, WellGroup, Well
from autoprotocol.container_type import _CONTAINER_TYPES
from autoprotocol.unit import Unit
from autoprotocol import UserError, Protocol
import sys

if sys.version_info[0] >= 3:
    string_type = str
else:
    string_type = basestring


def createMastermix(protocol, name, cont, reactions, resources={},
                    othermaterial={}, start_well=None, mm_mult=1.3,
                    use_safe_vol=True, use_dead_vol=False, columnwise=False):
    """Create simple or complex mastermixes from resourceIds or aliquots

    Creates a mix of the indicated reagents/resources for the number of
    reactions indicated. Balances the volume across the destination
    wells such that all but the last well carry the maximum number
    of reactions, the last well the overflow.
    Can account for dead_volume in each destination well.
    Can work with an existing mm container or create new ones and
    create new ones if existing ones are filled.
    You should only fill wells in order - so fill a container
    consistently with columnwise True or False throughout the protocol.
    Returns a list of wells. If you parsed in a container it is a good
    practice to check if you needed to make a new container and use
    that for future calls.
    Example: reagent_plate = unique_containers(target_wells)[-1]
    Otherwise you get a new plate everytime you try to fill the old one

    Parameters
    ----------
    protocol : Protocol
    name : str
        Well and or container name
    cont : str, Container
        String corresponding to wanted Container type or container
    reactions : int
        How many reactions to prepare
    resources : dict
        Dict with resource ids as keys and volume per reaction as value
    othermaterial : dict
        Dict with alliquot as key and volume per reaction as value
    start_well : int, optional
        Starting well for the container
    mm_mult : float, optional
        Multiplier used to account for overage
    use_dead_vol : bool, optional
        Account for dead_volume of container type
    columnwise : bool, optional


    Returns
    -------
    target_wells : list
        List of wells containing mastermix

    """
    if not isinstance(resources, dict):
        raise RuntimeError("To calculate a mastermix 'resources' has to be "
                           "a dict with resource ids as keys and "
                           "volume per reaction as value")
    if len(resources) > 0:
        for k, v in resources.iteritems():
            if not isinstance(v, (float, int, Unit)):
                raise RuntimeError("Values of the resources dict have to be "
                                   "volumes of type float, int or Unit.")
            if isinstance(v, Unit):
                resources[k] = v.value
            resources[k] = float(v)
            if 'rs' not in k:
                raise RuntimeError("Keys of the resources dict have to be "
                                   "resource ids starting with 'rs'.")

    if not isinstance(othermaterial, dict):
        raise RuntimeError("othermaterial has to be a dict with wells as "
                           "keys and volume per reaction as value.")
    if len(othermaterial) > 0:
        for k, v in othermaterial.iteritems():
            if not isinstance(v, (float, int, Unit)):
                raise RuntimeError("Values of the othermaterial dict have "
                                   "to be volumes of type float, int or "
                                   "Unit.")
            if isinstance(v, Unit):
                othermaterial[k] = v.value
            othermaterial[k] = float(v)

            if not isinstance(k, Well):
                raise RuntimeError("Keys of the othermaterial dict have to "
                                   "be wells")
    if not isinstance(reactions, int):
        raise RuntimeError("Reactions has to be an int")
    assert isinstance(name, string_type)
    if isinstance(cont, string_type):
        max_well_vol = 0.9 * _CONTAINER_TYPES[cont].well_volume_ul
        dead_vol = _CONTAINER_TYPES[cont].dead_volume_ul
        safe_vol = _CONTAINER_TYPES[cont].safe_min_volume_ul
    elif isinstance(cont, Container):
        max_well_vol = 0.9 * cont.container_type.well_volume_ul
        dead_vol = cont.container_type.dead_volume_ul
        safe_vol = cont.container_type.safe_min_volume_ul
    else:
        raise RuntimeError("cont for provision_group must be of type string"
                           " or container")

    if start_well is not None and not isinstance(start_well, int):
        raise RuntimeError("start_well can only be None or an integer")

    def emtpy_well(wells):
        verdict = True
        for well in wells:
            if well.volume is not None:
                verdict = False
                break
        return verdict

    # Set-up params and determine how much we need
    total_vol_per_reaction = (
        sum(resources.values()) + sum(othermaterial.values()))
    total_vol_pr_mm_mult = total_vol_per_reaction * mm_mult
    total_vol_all = total_vol_pr_mm_mult * reactions
    base_per_mm_well = 0.0
    if use_dead_vol:
        max_well_vol -= dead_vol
        base_per_mm_well += dead_vol
    if use_safe_vol:
        max_well_vol -= safe_vol
        base_per_mm_well += safe_vol
    # Determine mm well volume
    wells_needed = plates_needed(total_vol_all, max_well_vol)
    reactions_per_well = plates_needed(max_well_vol, total_vol_pr_mm_mult)

    if total_vol_pr_mm_mult > max_well_vol:
        raise RuntimeError("The mastermix volume for 1 reaction is bigger "
                           "than the maximum volume allowed in this "
                           "container: %s" % cont)
    # Make a list of volumes such that all but the last well
    # have the max number of reactions per well.
    # The last well has the reaction overfow.
    # Each has appropirate dead-volume if selected
    vol_per_mm_well = []
    while reactions > 0:
        if reactions > reactions_per_well:
            vol = total_vol_pr_mm_mult * reactions_per_well
            reactions -= reactions_per_well
        else:
            vol = total_vol_pr_mm_mult * reactions
            reactions -= reactions
        vol_per_mm_well.append(round(base_per_mm_well + vol, 2))

    # Set start well
    if not start_well:
        # New Container
        if isinstance(cont, str):
            start_well = 0
        else:
            # Container is empty
            filled_wells = [
                x.volume for x in cont.all_wells() if x.volume is not None]
            if len(filled_wells) == 0:
                start_well = 0
            # Container has content - select the first empty well
            else:
                if first_empty_well(cont).success:
                    start_well = first_empty_well(cont).well
                else:
                    start_well = 0
                    cont = cont.container_type.shortname

    target_wells = []
    # Make and prep containers
    # Check if we need to make containers
    if isinstance(cont, str):
        if cont in ('micro-1.5', 'micro-2.0'):
            for x in range(wells_needed):
                y = protocol.ref("%s-%s_%s" % (name,
                                               x + 1,
                                               printdate()),
                                 cont_type=cont,
                                 discard=True).well(0)
                y.set_name(name)
                target_wells.append(y)
        else:
            max_wells = float(_CONTAINER_TYPES[cont].well_count)
            num_plates = plates_needed(wells_needed, max_wells)
            temp_wells = wells_needed
            for x in range(num_plates):
                y = protocol.ref("%s-%s_%s" % (name,
                                               x + 1,
                                               printdate()),
                                 cont_type=cont,
                                 discard=True)
                len_wells = temp_wells if temp_wells < max_wells else max_wells
                z = y.wells_from(start_well,
                                 len_wells,
                                 columnwise=columnwise)
                if not emtpy_well(z):
                    raise RuntimeError("Not all wells are empty. "
                                       "Check your starting plate.")
                for i, well in enumerate(z):
                    well.set_name(name)
                target_wells.extend(z)
                temp_wells -= max_wells
    # Container got passsed along
    else:
        # If we don't have enough wells in the submitted container
        # Start with a new container of that type
        if (cont.container_type.well_count - start_well) < wells_needed:
            createMastermix(protocol,
                            name,
                            cont.container_type.shortname,
                            reactions,
                            resources,
                            othermaterial,
                            start_well=0,
                            mm_mult=mm_mult,
                            use_dead_vol=use_dead_vol)
        else:
            z = cont.wells_from(start_well,
                                wells_needed,
                                columnwise=columnwise)
            if not emtpy_well(z):
                raise RuntimeError("Not all wells are empty. "
                                   "Check your starting plate.")
            for i, well in enumerate(z):
                well.set_name(name)
            target_wells.extend(z)
    # Transfers
    # Determine the ratio of resources needed and provision them
    for k, v in resources.iteritems():
        ratio = v/total_vol_per_reaction
        vol = map((lambda x: Unit(round(x * ratio, 2), "microliter")),
                  vol_per_mm_well)
        protocol.provision(k, target_wells, vol)

    for k, v in othermaterial.iteritems():
        ratio = v/total_vol_per_reaction
        vol = map((lambda x: Unit(round(x * ratio, 2), "microliter")),
                  vol_per_mm_well)
        material_needed = total_vol_all * ratio
        # Check if well has enough
        if k.volume.value < material_needed:
            UserError("The following well does not have enough material for "
                      "all mm wells. Well: %s Volume available: %s Volume"
                      "  needed: %s" % (k, k.volume, material_needed))
        if (k.volume.value -
                k.container.container_type.dead_volume_ul) < material_needed:
            UserError("The following well does not have sufficient volume to"
                      " account for dead-volume. You may run short of liquid."
                      " Please use another aliquot or merge two aliquots. "
                      "Well: %s Volume available: %s "
                      "Volume needed: %s" % (k, k.volume, material_needed))
        protocol.transfer(k, target_wells, vol, new_group=True)

    if (len(resources) + len(othermaterial)) > 3:
        for well in target_wells:
            protocol.mix(well,
                         well.volume * 0.5,
                         repetitions=5)

    return target_wells


def serial_dilute_rowwise(protocol, source, well_group, vol,
                          mix_after=True, reverse=False):
    """
    Serial dilute source liquid in specified wells of the container
    specified. Defaults to dilute from left to right (increasing well index)
    unless reverse is set to true.  This operation utilizes the transfers()
    method on Pipette, meaning only one tip is used.  All wells in the
    WellGroup well_group except for the first and last well should already
    contain the diluent.

    Example Usage:

    .. code-block:: python

        p = Protocol()
        sample_plate = p.ref("sample_plate",
                             None,
                             "96-flat",
                             storage="warm_37")
        sample_source = p.ref("sample_source",
                              "ct32kj234l21g",
                              "micro-1.5",
                              storage="cold_20")

        p.serial_dilute_rowwise(sample_source.well(0),
                                sample_plate.wells_from(0,12),
                                "50:microliter",
                                mix_after=True)

    Parameters
    ----------
    container : Container
    source : Well
        Well containing source liquid.  Will be transfered to starting well,
        with double the volume specified in parameters
    start_well : Well
        Start of dilution, well containing the highest concentration of
        liquid
    end_well : Well
        End of dilution, well containing the lowest concentration of liquid
    vol : Unit, str
        Final volume of each well in the dilution series, most concentrated
        liquid will be transfered to the starting well with double this
        volume
    mix_after : bool, optional
        If set to True, each well will be mixed after liquid is transfered
        to it.
    reverse : bool, optional
        If set to True, liquid will be most concentrated in the well in the
        dilution series with the highest index

    """
    if not isinstance(well_group, WellGroup):
        raise RuntimeError("serial_dilute_rowwise() must take a WellGroup "
                           "as an argument")
    source_well = well_group.wells[0]
    begin_dilute = well_group.wells[0]
    end_dilute = well_group.wells[-1]
    wells_to_dilute = well_group[0].container.wells_from(
        begin_dilute,
        end_dilute.index-begin_dilute.index + 1)
    srcs = WellGroup([])
    dests = WellGroup([])
    vols = []
    if reverse:
        source_well = well_group.wells[-1]
        begin_dilute = well_group.wells[-1]
        end_dilute = well_group.wells[0]
        wells_to_dilute = well_group[0].container.wells_from(
            end_dilute,
            begin_dilute.index-end_dilute.index + 1)
    protocol.transfer(source.set_volume(Unit.fromstring(vol)*2),
                      source_well,
                      Unit.fromstring(vol)*2)
    if reverse:
        while len(wells_to_dilute.wells) >= 2:
            srcs.append(wells_to_dilute.wells.pop())
            dests.append(wells_to_dilute.wells[-1])
            vols.append(vol)
    else:
        for i in range(1, len(wells_to_dilute.wells)):
            srcs.append(wells_to_dilute.wells[i-1])
            dests.append(wells_to_dilute[i])
            vols.append(vol)
    protocol.transfer(srcs.set_volume(Unit.fromstring(vol)*2), dests, vols,
                      mix_after=mix_after, one_tip=True)


def autoseal(protocol, wells, covertype="standard", sealtype="ultra-clear"):
    """Determine whether to seal or cover a plate and do so

    Parameters
    ----------
    protocol: Protocol
        instance of autoprotocol Protocol
    wells: list, WellGroup, Container
        list of wells that need covering on the container level or container
    covertype: str, optional
        in case the plate needs to be covered, determine which covertype gets
        used. defaults to standard
    sealtype: str, optional
        in case the plate needs to be sealed, determine which seal type to
        select. defaults to ultra-clear

    """
    if isinstance(wells, (list, WellGroup)):
        to_seal = unique_containers(wells)
    elif isinstance(wells, Container):
        to_seal = [wells]
    else:
        raise RuntimeError("Wells has to be of type Well, WellGroup,"
                           "list of wells or container")
    assert isinstance(protocol, Protocol)

    for c in to_seal:
        if c.container_type.shortname in ["96-pcr", "384-pcr", "384-echo"]:
            protocol.seal(c, type=sealtype)
        elif c.container_type.shortname not in ["micro-1.5", "micro-2.0"]:
            protocol.cover(c, lid=covertype)
