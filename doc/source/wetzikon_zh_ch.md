# Wetzikon ZH, CH

Support for waste collection schedules of the city of [Wetzikon ZH](https://www.wetzikon.ch/).

## Configuration via configuration.yaml

```yaml
waste_collection_schedule:
    sources:
    - name: wetzikon_zh_ch
      args:
        region: 1
```

### Configuration Variables

**region**
*(Integer) (required)* with allowed values 1-4

## Example

```yaml
waste_collection_schedule:
    sources:
    - name: wetzikon_zh_ch
      args:
        region: 1
```

## How to get the source argument

An easy way to discover your region (Kreis) is to enter your address in their online tool [Waste Schedule Calendar and Region Map](https://m.wetzikon.ch/index.php?apid=7215088) or download the region map of Wetzikon and look up your address.

The region is important because the schedules differ between regions.