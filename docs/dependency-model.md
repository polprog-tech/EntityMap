# EntityMap Dependency Model

## Node Types

| Type | ID Format | Example | Description |
|---|---|---|---|
| `device` | `device.{id}` | `device.abc123` | Physical or virtual device from the device registry |
| `entity` | `{domain}.{id}` | `light.living_room` | Any entity not classified as another type |
| `automation` | `automation.{id}` | `automation.motion_light` | Automation entity |
| `script` | `script.{id}` | `script.dim_lights` | Script entity |
| `scene` | `scene.{id}` | `scene.evening` | Scene entity |
| `helper` | `{domain}.{id}` | `input_boolean.guest_mode` | Input helpers (input_boolean, input_number, etc.), counters, timers |
| `group` | `group.{id}` | `group.living_room_lights` | Group entity |
| `area` | `area.{id}` | `area.living_room` | Area from the area registry |

## Edge Types (DependencyKind)

| Kind | From → To | Description | Confidence |
|---|---|---|---|
| `entity_of_device` | Entity → Device | Entity belongs to this device (registry relationship) | High |
| `trigger` | Automation → Entity | Entity used as a trigger | High |
| `condition` | Automation → Entity | Entity checked in a condition | High |
| `action` | Automation/Script → Entity | Entity targeted in an action | High |
| `target` | Automation/Script → Entity | Entity used as a service target | High |
| `template_reference` | Any → Entity | Entity referenced in a Jinja2 template | Medium |
| `state_reference` | Any → Entity | Entity state read programmatically | Medium |
| `scene_member` | Scene → Entity | Entity is a member of this scene | High |
| `group_member` | Group → Entity | Entity is a member of this group | High |
| `service_call` | Automation/Script → Script/Scene | Calls another script or activates a scene | High |
| `device_trigger` | Automation → Device | Uses a device_id-based trigger | High |
| `device_condition` | Automation → Device | Uses a device_id-based condition | High |
| `device_action` | Automation/Script → Device | Uses a device_id-based action | High |
| `helper_reference` | Any → Helper | References a helper entity | High |
| `inferred` | Any → Any | Heuristically detected dependency | Low |

## Confidence Levels

| Level | Meaning | When Used |
|---|---|---|
| **High** | Confirmed direct reference in configuration | Registry relationships, explicit entity_id references |
| **Medium** | Extracted via pattern matching | Template references found by regex |
| **Low** | Heuristic/guess | Future use for advanced analysis |

## Edge Direction Convention

Edges always point from **dependent** to **dependency**:

```
automation.motion_light ──trigger──→ binary_sensor.motion
automation.motion_light ──action───→ light.living_room
light.living_room ──entity_of_device──→ device.abc123
```

This means:
- **Inbound edges** to a node = "what depends on this node"
- **Outbound edges** from a node = "what this node depends on"

## Breakage Scenarios

### Scenario 1: Removing a Zigbee device

```
device.zigbee_motion_sensor
  ← entity_of_device ← binary_sensor.motion
    ← trigger ← automation.motion_light
    ← condition ← automation.night_security
  ← device_trigger ← automation.motion_light (FRAGILE!)
```

**Impact**: 2 automations break. The device_trigger reference is especially fragile because the new device will get a different device_id.

**Recommendation**: Switch `automation.motion_light` to use entity-based triggers instead of device_id triggers. Note entity IDs before removal.

### Scenario 2: Disabling a helper

```
input_boolean.vacation_mode
  ← condition ← automation.lights_schedule
  ← condition ← automation.thermostat_eco
  ← template_reference ← sensor.home_status (INFERRED)
```

**Impact**: 2 automations will have stale conditions. The template sensor may show incorrect data.

**Recommendation**: Consider the downstream effects before disabling. If temporarily unused, leave enabled.

### Scenario 3: Script with hidden dependencies

```
automation.bedtime_routine
  ← service_call ← script.shutdown_house
    ← action ← light.bedroom
    ← action ← light.living_room
    ← action ← media_player.tv
    ← action ← lock.front_door
```

**Impact**: The automation appears to have 1 dependency (the script), but transitively depends on 4 entities. Changes to any of those entities may indirectly affect the automation.

## Migration Recommendations by Edge Type

| Edge Type | On Removal | On Replace | Recommended Action |
|---|---|---|---|
| `trigger` | Automation stops firing | Update entity_id in trigger | Edit automation trigger |
| `condition` | Condition may always fail/pass | Update entity_id in condition | Edit automation condition |
| `action` | Action fails silently or errors | Update entity_id in action target | Edit automation action |
| `device_trigger` | Automation stops firing | Must re-select device in UI | **Switch to entity trigger** |
| `device_condition` | Condition fails | Must re-select device in UI | **Switch to entity condition** |
| `device_action` | Action fails | Must re-select device in UI | **Switch to entity action** |
| `scene_member` | Scene incomplete | Add new entity to scene | Edit scene |
| `group_member` | Group incomplete | Add new entity to group | Edit group config |
| `entity_of_device` | Entity removed | New entities created | Rename new entity IDs to match old |
